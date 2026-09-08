<script setup lang="ts">
import { Search } from 'lucide-vue-next'

/**
 * Ô nhập mã cổ phiếu (dùng ở hero và ở CTA cuối trang chủ).
 * Chỉ nhận chữ và phát sự kiện — điều hướng do trang quyết định.
 */
const props = withDefaults(defineProps<{
  placeholder?: string
  buttonLabel?: string
  /**
   * hero = ô lớn có icon kính lúp; cta = ô gọn trong thẻ kêu gọi hành động.
   * Lớp CSS gắn tiền tố `s-`: scoped style của Vue đặt cả `data-v` của
   * component CHA lên thẻ gốc của con, nên nếu để trần `hero`/`cta` thì rule
   * `.hero` (HomeHero) và `.cta` (HomeCta) sẽ trúng luôn <form> này và phá layout.
   */
  variant?: 'hero' | 'cta'
}>(), {
  placeholder: 'Nhập mã cổ phiếu, VD: FPT',
  buttonLabel: 'Chấm điểm →',
  variant: 'hero'
})

const emit = defineEmits<{ submit: [code: string] }>()
const code = ref('')

/*
 * Gợi ý theo mã HOẶC tên công ty — người dùng nhớ "Vietcombank" chứ ít khi nhớ
 * "VCB". Danh bạ được backend cache 1 giờ nên gõ phím không gọi tới nguồn.
 */
interface Goi { symbol: string; name: string; exchange: string }

const config = useRuntimeConfig()
const apiBase = String(config.public.apiBase || '').replace(/\/+$/, '')

const goiY = ref<Goi[]>([])
const moGoiY = ref(false)
const chon = ref(-1)
let timer: ReturnType<typeof setTimeout> | null = null

function timGoiY(): void {
  //  Chống rung 200ms: gõ nhanh 6 ký tự chỉ nên là MỘT lần gọi API.
  if (timer) clearTimeout(timer)
  const q = code.value.trim()
  if (!q) {
    goiY.value = []
    moGoiY.value = false
    return
  }
  timer = setTimeout(async () => {
    try {
      goiY.value = await $fetch<Goi[]>(`${apiBase}/api/stocks/search`, { query: { q } })
      moGoiY.value = goiY.value.length > 0
      chon.value = -1
    } catch {
      //  Nguồn hỏng → không gợi ý, nhưng ô nhập vẫn dùng tay được như cũ.
      goiY.value = []
      moGoiY.value = false
    }
  }, 200)
}

function dongGoiY(): void {
  //  Chờ một nhịp: blur chạy TRƯỚC click, đóng ngay thì bấm vào gợi ý không ăn.
  setTimeout(() => (moGoiY.value = false), 150)
}

function chonMa(symbol: string): void {
  code.value = symbol
  moGoiY.value = false
  emit('submit', symbol)
}

function xuong(): void {
  if (moGoiY.value) chon.value = (chon.value + 1) % goiY.value.length
}

function len(): void {
  if (moGoiY.value) chon.value = (chon.value - 1 + goiY.value.length) % goiY.value.length
}

function onSubmit(): void {
  //  Đang chọn một gợi ý bằng bàn phím → Enter lấy đúng gợi ý đó.
  if (moGoiY.value && chon.value >= 0) {
    chonMa(goiY.value[chon.value]!.symbol)
    return
  }
  const c = code.value.trim().toUpperCase()
  if (c) emit('submit', c)
}
</script>

<template>
  <form class="tsearch" :class="'s-' + props.variant" @submit.prevent="onSubmit">
    <Search v-if="props.variant === 'hero'" class="ic" />
    <input
      v-model="code"
      :placeholder="props.placeholder"
      aria-label="Mã cổ phiếu"
      autocapitalize="characters"
      spellcheck="false"
      maxlength="12"
      autocomplete="off"
      role="combobox"
      aria-autocomplete="list"
      :aria-expanded="moGoiY"
      @input="timGoiY"
      @keydown.down.prevent="xuong"
      @keydown.up.prevent="len"
      @keydown.esc="moGoiY = false"
      @blur="dongGoiY"
    />
    <button type="submit">{{ props.buttonLabel }}</button>

    <ul v-if="moGoiY" class="goi-y" role="listbox">
      <li v-for="(g, i) in goiY" :key="g.symbol" :class="{ on: i === chon }" role="option"
          :aria-selected="i === chon">
        <button type="button" @mousedown.prevent="chonMa(g.symbol)">
          <b>{{ g.symbol }}</b>
          <span class="ten">{{ g.name }}</span>
          <span class="san">{{ g.exchange }}</span>
        </button>
      </li>
    </ul>
  </form>
</template>

<style scoped>
/*  Danh sách gợi ý: form là `position: relative` sẵn ở cả hai biến thể nên thả
    tuyệt đối ngay dưới ô nhập. z-index cao hơn dải giá chạy phía dưới hero. */
.tsearch { position: relative; }

.goi-y {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 40;
  margin: 0;
  padding: 4px;
  list-style: none;
  text-align: left;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel-solid, #0f1626);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.45);
  max-height: 300px;
  overflow-y: auto;
}

.goi-y li button {
  display: flex;
  align-items: baseline;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  border-radius: 8px;
  background: none;
  color: var(--text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.goi-y li.on button,
.goi-y li button:hover { background: var(--panel2); }
.goi-y b { color: var(--accent); font-size: 13px; min-width: 62px; }
.goi-y .ten { flex: 1; font-size: 12.5px; color: var(--muted); overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; }
.goi-y .san { font-size: 11px; color: var(--muted-2); }

.tsearch { display: flex; align-items: center; gap: 8px; background: var(--panel-solid);
  border: 1px solid var(--line-hi); border-radius: 14px; padding: 6px 6px 6px 14px;
  color: var(--muted); transition: border-color 0.2s; }
.tsearch.s-hero { max-width: 560px; margin: 0 auto; box-shadow: 0 12px 30px -18px rgba(0, 0, 0, 0.8); }
.tsearch.s-cta { background: var(--panel-deep); }
.tsearch:focus-within { border-color: var(--accent); }
.ic { flex: none; }
.tsearch input { flex: 1; min-height: 44px; min-width: 0; background: none; border: none; outline: none;
  color: var(--text); font-size: 17px; font-weight: 600; letter-spacing: 0.6px;
  text-transform: uppercase; font-family: var(--mono); }
.tsearch input::placeholder { color: var(--muted-2); text-transform: none; font-family: var(--sans); font-weight: 400; letter-spacing: 0; }
.tsearch button { background: var(--accent); color: var(--on-accent); border: none; border-radius: 10px;
  padding: 0 18px; min-height: 44px; font-size: 14.5px; font-weight: 700; cursor: pointer;
  font-family: var(--sans); white-space: nowrap; box-shadow: 0 6px 16px -10px rgba(90, 200, 255, 0.6); }
.tsearch button:hover { background: var(--accent-hi); }

@media (max-width: 700px) {
  .tsearch { gap: 6px; padding: 5px 5px 5px 12px; }
  .tsearch input { min-height: 46px; }
  .tsearch button { min-height: 46px; padding: 0 16px; }
}
</style>
