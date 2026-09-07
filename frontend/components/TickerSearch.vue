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

function onSubmit(): void {
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
    />
    <button type="submit">{{ props.buttonLabel }}</button>
  </form>
</template>

<style scoped>
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
