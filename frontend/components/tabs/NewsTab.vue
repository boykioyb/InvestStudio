<script setup lang="ts">
/** Tab Tin tức: tin công bố + sự kiện doanh nghiệp. */
const props = defineProps<{ ticker: string }>()

const { news, isLoading, errorOf, loadNews } = useStockDetails()
const key = computed(() => `${props.ticker.toUpperCase()}:news`)

watch(() => props.ticker, (t) => t && loadNews(t), { immediate: true })
</script>

<template>
  <div class="tab-body">
    <p v-if="errorOf(key)" class="msg error" role="alert">{{ errorOf(key) }}</p>
    <p v-else-if="isLoading(key)" class="hint">Đang tải tin tức…</p>

    <template v-else-if="news">
      <p class="msg warn">{{ news.note }}</p>

      <section v-if="news.disclosure_links?.length" class="card official">
        <h3 class="sec-title">Đọc bản gốc ở đâu</h3>
        <p class="hint">
          Toàn văn công bố thông tin nằm trên trang của sở giao dịch — đây là nguồn
          chính thức, đáng tin hơn mọi bản tin tóm tắt.
        </p>
        <div class="off-links">
          <a
            v-for="l in news.disclosure_links"
            :key="l.url"
            :href="l.url"
            target="_blank"
            rel="noopener noreferrer"
            class="off-link"
          >{{ l.label }} ↗</a>
        </div>
      </section>

      <div class="cols">
        <section class="card">
          <h3 class="sec-title">Tin công bố ({{ news.news.length }})</h3>
          <div v-for="(n, i) in news.news" :key="i" class="item">
            <span class="date tnum">{{ n.date || '—' }}</span>
            <span class="title">
              <span>{{ n.title }}</span>
              <span v-if="n.links?.length" class="links">
                <a
                  v-for="l in n.links"
                  :key="l.url"
                  :href="l.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="link"
                >{{ l.label }} ↗</a>
              </span>
            </span>
          </div>
          <p v-if="!news.news.length" class="hint">Chưa có tin nào.</p>
        </section>

        <section class="card">
          <h3 class="sec-title">Sự kiện doanh nghiệp ({{ news.events.length }})</h3>
          <div v-for="(e, i) in news.events" :key="i" class="item">
            <span class="date tnum">{{ e.date || '—' }}</span>
            <span class="title">
              <b class="ev-name">{{ e.name }}</b>
              <span v-if="e.title" class="ev-title">{{ e.title }}</span>
            </span>
          </div>
          <p v-if="!news.events.length" class="hint">Chưa có sự kiện nào.</p>
        </section>
      </div>
    </template>

    <p v-else class="hint">Chưa có dữ liệu tin tức.</p>
  </div>
</template>

<style scoped>
.cols {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 12px;
  align-items: start;
}

.item {
  display: flex;
  gap: 12px;
  padding: 7px 0;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  line-height: 1.45;
}

.item:last-child {
  border-bottom: none;
}

.date {
  flex: none;
  width: 82px;
  color: var(--muted);
  font-size: 12px;
}

.title {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.ev-name {
  color: var(--accent);
  font-size: 12px;
}

.ev-title {
  color: var(--muted);
}

.links {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 3px;
}

.link {
  font-size: 11.5px;
  color: var(--accent);
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.official {
  border-color: var(--accent);
}

.off-links {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.off-link {
  border: 1px solid var(--line);
  background: var(--panel2);
  border-radius: 8px;
  padding: 8px 13px;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  text-decoration: none;
}

.off-link:hover {
  border-color: var(--accent);
}
</style>
