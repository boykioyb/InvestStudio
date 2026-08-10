<script setup lang="ts">
/**
 * Nút ⭐ thêm/bỏ một mã khỏi danh sách theo dõi.
 *
 * Tự lo trạng thái đăng nhập: chưa đăng nhập thì bấm sẽ chuyển sang trang đăng
 * nhập (kèm đường dẫn quay lại). Mọi thao tác dữ liệu đều qua composable —
 * thành phần này chỉ hiển thị và gọi hàm.
 */
const props = defineProps<{ ticker: string }>()

const { isLoggedIn, ensureLoaded } = useAuth()
const { has, load, loaded, add, removeByTicker } = useWatchlist()
const route = useRoute()
const busy = ref(false)

const code = computed(() => props.ticker.toUpperCase().trim())
const active = computed(() => has(code.value))

onMounted(async () => {
  await ensureLoaded()
  if (isLoggedIn.value && !loaded.value) await load()
})

async function toggle(): Promise<void> {
  if (!isLoggedIn.value) {
    //  Lưu đường dẫn hiện tại để đăng nhập xong quay lại đúng chỗ.
    void navigateTo({ path: '/dang-nhap', query: { next: route.fullPath } })
    return
  }
  busy.value = true
  try {
    if (active.value) await removeByTicker(code.value)
    else await add({ ticker: code.value })
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <button
    type="button"
    class="fav"
    :class="{ on: active }"
    :disabled="busy"
    :title="active ? `Bỏ theo dõi ${code}` : `Theo dõi ${code}`"
    @click="toggle"
  >
    <span aria-hidden="true">{{ active ? '★' : '☆' }}</span>
    <span class="lb">{{ active ? 'Đang theo dõi' : 'Theo dõi' }}</span>
  </button>
</template>

<style scoped>
.fav {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  font-weight: 700;
  border: 1px solid var(--line);
  background: var(--panel2);
  color: var(--text);
  border-radius: 20px;
  padding: 4px 10px;
  cursor: pointer;
  white-space: nowrap;
}

.fav:hover:not(:disabled) {
  border-color: var(--warn);
  color: var(--warn);
}

.fav.on {
  border-color: var(--warn);
  color: var(--warn);
  background: var(--warn-soft);
}

.fav:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
