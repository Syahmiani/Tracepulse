export default function StatusCard({label, value, tone = "safe"}) {
    return <article className={`dashboard-status-card dashboard-status-card--${tone}`}>
        <span>{label}</span>
        <strong>{value}</strong>
    </article>;
}
