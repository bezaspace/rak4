type Props = {
  status: string;
  warning: string;
};

export function StatusPanel({ status, warning }: Props) {
  return (
    <section style={{ border: "1px solid #cdd4d8", borderRadius: 8, padding: 12, background: "#f7fbfc" }}>
      <div>
        <strong>Status:</strong> {status}
      </div>
      {warning ? (
        <div style={{ marginTop: 8, color: "#8a3c00" }}>
          <strong>Safety note:</strong> {warning}
        </div>
      ) : null}
    </section>
  );
}
