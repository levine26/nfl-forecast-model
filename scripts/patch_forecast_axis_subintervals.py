from pathlib import Path

path = Path('site/src/AppPublicationVNext.jsx')
text = path.read_text()
text = text.replace(
    "import { Area, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'",
    "import { Area, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'",
)
old = """  const ticks = [0,1,2,3,4,5,6].filter(value=>value<=axisEnd+0.001)\n  const labelForTick = value => DAY_LABELS[Math.round(value)] || ''\n  const tooltipTime = payload => {"""
new = """  const majorTicks = [0,1,2,3,4,5,6].filter(value=>value<=axisEnd+0.001)\n  const ticks = []\n  for (let value=0; value<=axisEnd+0.001; value+=1/3) ticks.push(Number(value.toFixed(6)))\n  const minorTicks = ticks.filter(value=>Math.abs(value-Math.round(value))>0.01)\n  const axisTick = ({x,y,payload}) => {\n    const value = Number(payload?.value)\n    const day = Math.round(value)\n    const isDay = Math.abs(value-day) < 0.01\n    if (isDay) return <text x={x} y={y+16} textAnchor=\"middle\" fill=\"#d7e4ec\" fontSize=\"11\" fontWeight=\"700\">{DAY_LABELS[day] || ''}</text>\n    const fraction = value-Math.floor(value)\n    const label = Math.abs(fraction-1/3)<0.03 ? '8 AM' : Math.abs(fraction-2/3)<0.03 ? '4 PM' : ''\n    return <text x={x} y={y+15} textAnchor=\"middle\" fill=\"#6f8796\" fontSize=\"9\">{label}</text>\n  }\n  const tooltipTime = payload => {"""
if old not in text:
    raise SystemExit('weekday tick block not found')
text = text.replace(old, new)
old_chart = """<LineChart data={trend} margin={{top:10,right:10,left:-10,bottom:0}}><CartesianGrid stroke=\"#183041\" strokeDasharray=\"3 5\" vertical={false}/><XAxis type=\"number\" dataKey=\"x\" domain={[0,axisEnd]} ticks={ticks} tickFormatter={labelForTick} tickLine={false} axisLine={false}/><YAxis domain={[0.35,.85]} tickFormatter={v=>`${Math.round(v*100)}%`} tickLine={false} axisLine={false}/><Tooltip"""
new_chart = """<LineChart data={trend} margin={{top:10,right:10,left:-10,bottom:8}}><CartesianGrid stroke=\"#183041\" strokeDasharray=\"3 5\" vertical={false}/>{minorTicks.map(value=><ReferenceLine key={`minor-${value}`} x={value} stroke=\"#132b3a\" strokeWidth={1}/>) }{majorTicks.map(value=><ReferenceLine key={`major-${value}`} x={value} stroke=\"#294759\" strokeWidth={1.35}/>) }<XAxis type=\"number\" dataKey=\"x\" domain={[0,axisEnd]} ticks={ticks} interval={0} tick={axisTick} tickLine={false} axisLine={false} height={34}/><YAxis domain={[0.35,.85]} tickFormatter={v=>`${Math.round(v*100)}%`} tickLine={false} axisLine={false}/><Tooltip"""
if old_chart not in text:
    raise SystemExit('forecast chart block not found')
text = text.replace(old_chart, new_chart)
path.write_text(text)
