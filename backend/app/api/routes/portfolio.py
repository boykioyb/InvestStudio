"""Danh mục tổng quan: đánh giá nhiều mã cùng lúc (chỉ giá + lãi/lỗ).

Ngoài `/review` (nhập tay, lưu ở trình duyệt), còn có luồng ĐỒNG BỘ từ công ty
chứng khoán qua extension:
  • `/import-token` — người dùng đã đăng nhập trên web tạo token dán vào extension.
  • `/import`       — extension gửi danh mục kèm token đó (KHÔNG cần cookie web).
  • `/holdings`     — web đọc lại danh mục đã đồng bộ để chấm điểm từng mã.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import plans, ratelimit
from app.core.security import create_purpose_token, decode_purpose_token
from app.db.session import get_db
from app.models.portfolio import ImportedHolding, ImportedLot
from app.models.user import User
from app.schemas.stock import (
    ImportedHoldingOut,
    ImportedLotOut,
    ImportTokenOut,
    PortfolioImportRequest,
    PortfolioImportResult,
    PortfolioLotsImportRequest,
    PortfolioLotsImportResult,
    PortfolioRequest,
    PortfolioReview,
)
from app.services import portfolio
from app.services.providers.base import ProviderError

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

#  Token đồng bộ dùng riêng một "purpose": lấy được nó cũng KHÔNG đăng nhập web
#  được, chỉ gọi được đúng /import. Sống 30 ngày, đổi mật khẩu là hết hiệu lực
#  (nhúng token_version, kiểm lại khi dùng).
_IMPORT_PURPOSE = "portfolio-import"
_IMPORT_TOKEN_DAYS = 30


@router.post("/review", response_model=PortfolioReview,
             summary="Tổng quan danh mục: lãi/lỗ toàn bộ vị thế theo giá hiện tại")
def portfolio_review(payload: PortfolioRequest, request: Request,
                     user: User = Depends(get_current_user)) -> PortfolioReview:
    """Gộp các đợt mua của nhiều mã, lấy giá cả danh mục trong một request.

    KHÔNG cache: phụ thuộc các đợt mua người dùng vừa nhập. KHÔNG chấm điểm —
    điểm số/khuyến nghị từng mã xem ở endpoint `/stocks/{ticker}/position`.

    YÊU CẦU ĐĂNG NHẬP (H7): một request gọi được tới 100 mã, tức khuếch đại
    thành hàng trăm lượt crawl — nguồn chặn ở ~20 request/phút, bị chặn là CẢ
    trang chết. Mỗi lượt cũng tính vào hạn mức phân tích trong ngày.
    """
    #  Cùng rổ "analyze" với stocks.py:`_analyze_quota` → phải dùng CÙNG cách
    #  giải hạn mức (trước đây chỗ này đọc thẳng config, bỏ qua /admin).
    ratelimit.enforce_daily(f"u:{user.id}", "analyze",
                            plans.effective(user, "analyze"), fail_open=True)
    try:
        return portfolio.review(payload)
    except ProviderError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/import-token", response_model=ImportTokenOut,
             summary="Tạo token để extension đồng bộ danh mục (đang đăng nhập web)")
def create_import_token(user: User = Depends(get_current_user)) -> ImportTokenOut:
    """Người dùng bấm trên web (đã đăng nhập cookie) để lấy token dán vào extension.

    Token CHỈ dùng được cho `/import` (purpose riêng), nên kể cả lộ cũng không ai
    đăng nhập hay đọc dữ liệu khác của bạn được.
    """
    token = create_purpose_token(
        user.id, _IMPORT_PURPOSE, _IMPORT_TOKEN_DAYS * 24 * 60,
        extra={"tv": user.token_version})
    return ImportTokenOut(token=token, expires_days=_IMPORT_TOKEN_DAYS,
                          email=user.email, name=user.display_name or "")


def _user_from_import_token(request: Request, db: Session) -> User | None:
    """Giải token đồng bộ ở header Authorization: Bearer. None nếu không phải."""
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    claims = decode_purpose_token(auth[7:].strip(), _IMPORT_PURPOSE)
    if claims is None:
        return None
    sub = str(claims.get("sub", ""))
    if not sub.isdigit():
        return None
    user = db.get(User, int(sub))
    if user is None or user.status != "active":
        return None
    #  Đổi mật khẩu / bị khóa → token_version tăng → token đồng bộ cũ hết hiệu lực.
    if int(claims.get("tv", 0)) != user.token_version:
        return None
    return user


@router.post("/import", response_model=PortfolioImportResult,
             summary="Đồng bộ danh mục từ công ty chứng khoán (extension TCBS)")
def import_holdings(payload: PortfolioImportRequest, request: Request,
                    db: Session = Depends(get_db)) -> PortfolioImportResult:
    """Nhận danh mục từ extension và LƯU ĐÈ toàn bộ vị thế đã đồng bộ của user.

    Xác thực bằng token đồng bộ (`/import-token`) ở header Authorization, hoặc
    cookie/Bearer đăng nhập thường (khi web tự gọi). KHÔNG lưu token TCBS.
    """
    user = _user_from_import_token(request, db)
    if user is None:
        #  Không có token đồng bộ hợp lệ → thử phiên đăng nhập thường (raise 401).
        user = get_current_user(request, db)

    #  Lãi/lỗ ĐÃ THỰC HIỆN theo mã (nếu extension gửi kèm).
    realized: dict[str, float | None] = {}
    for r in payload.realized:
        code = r.ticker.upper().strip()
        if code:
            realized[code] = r.actual_pnl

    #  Gộp trùng mã (đề phòng extension gửi lặp), chuẩn hóa mã hoa.
    merged: dict[str, dict] = {}
    for item in payload.holdings:
        code = item.ticker.upper().strip()
        if not code:
            continue
        merged[code] = {
            "quantity": float(item.qty or 0),
            "avg_price": item.avg_price,
            "market_price": item.market_price,
        }

    #  LƯU ĐÈ: xóa danh mục đồng bộ cũ rồi ghi mới — đúng ảnh chụp hiện tại.
    db.execute(delete(ImportedHolding).where(ImportedHolding.user_id == user.id))
    for code, v in merged.items():
        db.add(ImportedHolding(
            user_id=user.id, ticker=code, quantity=v["quantity"],
            avg_price=v["avg_price"], market_price=v["market_price"],
            realized_pnl=realized.pop(code, None),
            source=payload.source or "TCBS", account_no=payload.account or ""))
    #  Mã đã BÁN HẾT (không còn nắm giữ) nhưng có lãi/lỗ đã thực hiện: vẫn lưu để
    #  người dùng thấy kết quả chốt lời/lỗ, quantity = 0.
    for code, pnl in realized.items():
        db.add(ImportedHolding(
            user_id=user.id, ticker=code, quantity=0.0,
            avg_price=None, market_price=None, realized_pnl=pnl,
            source=payload.source or "TCBS", account_no=payload.account or ""))
    db.commit()

    rows = db.scalars(
        select(ImportedHolding).where(ImportedHolding.user_id == user.id)).all()
    updated = max((r.updated_at for r in rows if r.updated_at), default=None)
    return PortfolioImportResult(
        imported=len(merged),
        tickers=sorted(merged.keys()),
        account=payload.account or "",
        updated_at=updated.isoformat() if updated else "",
    )


@router.post("/import-lots", response_model=PortfolioLotsImportResult,
             summary="Đồng bộ từng đợt khớp (mua/bán) từ lịch sử lệnh TCBS")
def import_lots(payload: PortfolioLotsImportRequest, request: Request,
                db: Session = Depends(get_db)) -> PortfolioLotsImportResult:
    """LƯU ĐÈ toàn bộ đợt khớp đã đồng bộ của user (dựng lại 'Vị thế của tôi')."""
    user = _user_from_import_token(request, db)
    if user is None:
        user = get_current_user(request, db)

    db.execute(delete(ImportedLot).where(ImportedLot.user_id == user.id))
    tickers: set[str] = set()
    for lot in payload.lots:
        code = lot.ticker.upper().strip()
        if not code:
            continue
        tickers.add(code)
        db.add(ImportedLot(
            user_id=user.id, ticker=code, side=lot.side, quantity=float(lot.qty or 0),
            price=float(lot.price or 0), fee=lot.fee, tax=lot.tax,
            txdate=lot.txdate or "", order_id=lot.order_id or "",
            source=payload.source or "TCBS"))
    db.commit()
    return PortfolioLotsImportResult(imported=len(payload.lots), tickers=sorted(tickers))


@router.get("/lots", response_model=list[ImportedLotOut],
            summary="Các đợt khớp đã đồng bộ (đang đăng nhập) — để nhập vào Vị thế của tôi")
def list_lots(user: User = Depends(get_current_user),
              db: Session = Depends(get_db)) -> list[ImportedLotOut]:
    rows = db.scalars(
        select(ImportedLot)
        .where(ImportedLot.user_id == user.id)
        .order_by(ImportedLot.ticker, ImportedLot.txdate)).all()
    return [
        ImportedLotOut(
            ticker=r.ticker, side=r.side, quantity=r.quantity, price=r.price,
            fee=r.fee, tax=r.tax, txdate=r.txdate, order_id=r.order_id)
        for r in rows
    ]


@router.get("/holdings", response_model=list[ImportedHoldingOut],
            summary="Danh mục đã đồng bộ từ công ty chứng khoán (đang đăng nhập)")
def list_holdings(user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> list[ImportedHoldingOut]:
    rows = db.scalars(
        select(ImportedHolding)
        .where(ImportedHolding.user_id == user.id)
        .order_by(ImportedHolding.ticker)).all()
    return [
        ImportedHoldingOut(
            ticker=r.ticker, quantity=r.quantity, avg_price=r.avg_price,
            market_price=r.market_price, realized_pnl=r.realized_pnl,
            source=r.source, account_no=r.account_no,
            updated_at=r.updated_at.isoformat() if r.updated_at else None)
        for r in rows
    ]
