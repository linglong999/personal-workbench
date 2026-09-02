import HealthWidget from './HealthWidget.jsx'
import PlaceholderWidget from './PlaceholderWidget.jsx'

/* widget 注册表：M4 接入真实数据源时在此换 component 即可，容器不动。
   契约：entry = { id, title, size: {x,y,w,h}, component, props? }；
   component 接收 { tick, cfg }——tick 由面板 ↻ 注入（手动刷新），cfg = entry.props。
   数组（非对象 map）：保序，首个渲染位置即默认布局。 */
export const REGISTRY = [
  {
    id: 'bridge-health',
    title: '服务健康',
    size: { x: 0, y: 0, w: 3, h: 2 },
    component: HealthWidget,
  },
  {
    id: 'knowledge-stock',
    title: '知识存量',
    size: { x: 3, y: 0, w: 4, h: 3 },
    component: PlaceholderWidget,
    props: { hint: '知识卡片数量 / 分类分布（Vault + Chroma 统计）' },
  },
  {
    id: 'usage-trend',
    title: '用量趋势',
    size: { x: 7, y: 0, w: 5, h: 3 },
    component: PlaceholderWidget,
    props: { hint: 'token 消耗与成本的时间趋势（usage_records 聚合端点）' },
  },
  {
    id: 'external-feed',
    title: '外部数据',
    size: { x: 3, y: 3, w: 7, h: 2 },
    component: PlaceholderWidget,
    props: { hint: '天气 · 日历 · RSS 等外部数据源（M4 以后评估接入）' },
  },
]
