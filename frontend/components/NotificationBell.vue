<script setup lang="ts">
/**
 * Chuông thông báo trên header. Hiện số chưa đọc; mở ra xem danh sách cảnh báo
 * ngưỡng theo dõi. Chỉ hiển thị khi đã đăng nhập (đặt bên trong AuthNav).
 */
import { Bell } from 'lucide-vue-next'

const { items, unread, fetchUnread, load, markRead, markAllRead } = useNotifications()
const open = ref(false)
let poll: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  void fetchUnread()
  //  Cập nhật số chưa đọc định kỳ (job nền tạo thông báo mỗi 30 phút).
  poll = setInterval(() => void fetchUnread(), 60_000)
})
onBeforeUnmount(() => {
  if (poll) clearInterval(poll)
})

async function toggle(): Promise<void> {
  open.value = !open.value
  if (open.value) await load()
}
</script>

<template>
  <div class="bell-wrap">
    <button type="button" class="bell" :class="{ has: unread > 0 }"
            :aria-label="`Thông báo (${unread} chưa đọc)`" @click="toggle">
      <Bell />
      <span v-if="unread > 0" class="badge">{{ unread > 9 ? '9+' : unread }}</span>
    </button>

    <div v-if="open" class="panel" role="dialog" aria-label="Thông báo">
      <header class="head">
        <span>Thông báo</span>
        <button v-if="items.some((n) => !n.is_read)" type="button" class="link"
                @click="markAllRead">Đánh dấu đã đọc</button>
      </header>
      <p v-if="!items.length" class="empty">Chưa có cảnh báo nào.</p>
      <ul v-else class="list">
        <li v-for="n in items" :key="n.id" :class="{ unread: !n.is_read }"
            @click="markRead(n.id)">
          <span class="tag" :class="n.kind">{{ n.ticker }}</span>
          <span class="msg">{{ n.message }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.bell-wrap {
  position: relative;
}

.bell {
  position: relative;
  display: inline-flex;
  align-items: center;
  background: none;
  border: 0;
  color: var(--muted);
  cursor: pointer;
  padding: 2px;
}

.bell.has {
  color: var(--warn);
}

.badge {
  position: absolute;
  top: -5px;
  right: -6px;
  background: var(--bad);
  color: #fff;
  font-size: 9px;
  font-weight: 800;
  border-radius: 999px;
  padding: 0 4px;
  line-height: 14px;
}

.panel {
  position: absolute;
  right: 0;
  top: 130%;
  width: min(340px, calc(100vw - 24px));
  max-height: 60vh;
  overflow-y: auto;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: 0 18px 44px rgba(0, 0, 0, 0.5);
  z-index: 70;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
  font-weight: 700;
  font-size: 13px;
}

.link {
  background: none;
  border: 0;
  color: var(--accent);
  font-size: 11.5px;
  cursor: pointer;
}

.empty {
  padding: 16px 12px;
  color: var(--muted);
  font-size: 13px;
  margin: 0;
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.list li {
  display: flex;
  gap: 8px;
  align-items: baseline;
  padding: 9px 12px;
  border-bottom: 1px solid var(--line);
  font-size: 12.5px;
  cursor: pointer;
}

.list li.unread {
  background: rgba(90, 200, 255, 0.06);
}

.list li:hover {
  background: var(--panel2);
}

.tag {
  font-weight: 800;
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: 8px;
  flex: none;
  color: #04121f;
  background: var(--accent);
}

.tag.score {
  background: var(--good);
}

.msg {
  color: var(--text);
}
</style>
