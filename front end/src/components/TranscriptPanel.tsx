type Props = {
  userTranscript: string;
  assistantMessages: string[];
};

export function TranscriptPanel({ userTranscript, assistantMessages }: Props) {
  return (
    <section style={{ border: "1px solid #cdd4d8", borderRadius: 8, padding: 12, background: "#ffffff" }}>
      <h3 style={{ marginTop: 0 }}>Live Transcript</h3>
      <p>
        <strong>You:</strong> {userTranscript || "(listening...)"}
      </p>
      <div>
        <strong>Raksha:</strong>
        <ul>
          {assistantMessages.map((msg, idx) => (
            <li key={`${idx}-${msg.slice(0, 10)}`}>{msg}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
