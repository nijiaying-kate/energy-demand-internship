"use client";

import { useMemo, useState } from "react";
import dashboardData from "../public/data/dashboard-data.json";

const demand = dashboardData.forecast.map((item) => item.predictedQty);
const dates = dashboardData.forecast.map((item) => item.targetDate.slice(5).replace("-", "/"));

export default function Home() {
  const [initial, setInitial] = useState(50000);
  const [safety, setSafety] = useState(15000);
  const [supply, setSupply] = useState(30000);
  const rows = useMemo(() => {
    let stock = initial, replenished = false;
    return demand.map((predictedQty, i) => {
      const before = stock - predictedQty;
      const replenishment = before <= safety && !replenished ? supply : 0;
      stock = before + replenishment;
      replenished ||= replenishment > 0;
    return { date: dates[i], predictedQty, before, replenishment, stock };
    });
  }, [initial, safety, supply]);
  const total = demand.reduce((a, b) => a + b, 0);
  const replenishmentDate = rows.find((r) => r.replenishment > 0)?.date ?? "不要";
  const maxDemand = Math.max(...demand);
  const chartMax = Math.max(initial, ...rows.map((r) => r.stock), safety) * 1.08;
  const points = rows.map((r, i) => `${42 + i * 75},${178 - (r.stock / chartMax) * 142}`).join(" ");

  return <main>
    <header className="hero"><div><p className="eyebrow">DEMAND FORECAST</p><h1>需要予測ダッシュボード</h1><p className="muted">対象拠点: {dashboardData.locationId}　/　モデル: {dashboardData.modelName}　/　予測基準日: {dashboardData.forecastOrigin}</p></div><span className="status">● 予測済み</span></header>

    <section className="kpis">
      <Kpi label="7日累計需要" value={`${total.toLocaleString()} L`} note="平均 ${Math.round(total / 7).toLocaleString()} L / 日" />
      <Kpi label="安全在庫到達・補充日" value={replenishmentDate} note={replenishmentDate === "不要" ? "補充不要" : "安全在庫を下回る最初の日"} accent />
      <Kpi label="7日後在庫" value={`${Math.round(rows.at(-1)?.stock ?? 0).toLocaleString()} L`} note={`Test WAPE ${dashboardData.metrics.testWape.toFixed(2)}%`} />
    </section>

    <section className="grid two"><article className="panel"><div className="panel-title"><div><p className="eyebrow">DEMAND</p><h2>7日需要予測</h2></div><b>単位: L</b></div><div className="bar-chart">{demand.map((value, i) => <div className="bar-wrap" key={dates[i]}><span>{(value / 1000).toFixed(1)}k</span><div className="bar" style={{ height: `${(value / maxDemand) * 150}px` }} /><small>{dates[i]}</small></div>)}</div></article>
      <article className="panel"><div className="panel-title"><div><p className="eyebrow">INVENTORY</p><h2>在庫推移</h2></div><b className="teal">補充後在庫</b></div><svg viewBox="0 0 500 210" role="img" aria-label="在庫推移グラフ"><line x1="36" x2="490" y1={178 - (safety / chartMax) * 142} y2={178 - (safety / chartMax) * 142} className="safety"/><text x="38" y={172 - (safety / chartMax) * 142}>安全在庫</text><polyline points={`42,${178 - (initial / chartMax) * 142} ${points}`} className="stock-line"/>{rows.map((r,i)=><g key={r.date}><circle cx={42+i*75} cy={178-(r.stock/chartMax)*142} r="4"/><text x={32+i*75} y="200">{r.date}</text></g>)}</svg></article></section>

    <section className="panel controls"><div><p className="eyebrow">SIMULATION</p><h2>在庫条件を変更する</h2></div><div className="input-grid"><NumberInput label="初期在庫" value={initial} setValue={setInitial}/><NumberInput label="安全在庫" value={safety} setValue={setSafety}/><NumberInput label="補充量（1回）" value={supply} setValue={setSupply}/></div></section>

    <section className="panel"><div className="panel-title"><div><p className="eyebrow">DETAIL</p><h2>日別予測・在庫明細</h2></div><b>単位: L</b></div><div className="table-scroll"><table><thead><tr><th>日付</th><th>予測需要</th><th>補充前在庫</th><th>補充量</th><th>終了在庫</th><th>状態</th></tr></thead><tbody>{rows.map(r=><tr key={r.date}><td>{r.date}</td><td>{r.predictedQty.toLocaleString()}</td><td>{Math.round(r.before).toLocaleString()}</td><td>{r.replenishment ? `+${r.replenishment.toLocaleString()}` : "—"}</td><td>{Math.round(r.stock).toLocaleString()}</td><td><span className={r.replenishment ? "pill active" : "pill"}>{r.replenishment ? "補充実施" : "通常"}</span></td></tr>)}</tbody></table></div></section>
  </main>;
}

function Kpi({ label, value, note, accent = false }: { label: string; value: string; note: string; accent?: boolean }) { return <article className={`kpi ${accent ? "accent" : ""}`}><span>{label}</span><strong>{value}</strong><small>{note}</small></article>; }
function NumberInput({ label, value, setValue }: { label: string; value: number; setValue: (n: number) => void }) { return <label>{label}<div><input type="number" min="0" value={value} onChange={(e) => setValue(Number(e.target.value))}/><span>L</span></div></label>; }
