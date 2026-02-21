import type { BookingCard } from "../lib/liveSocket";

type BookingUpdate = {
  status: "confirmed" | "failed" | "unavailable" | "needs_confirmation";
  message: string;
  booking?: BookingCard;
};

type Props = {
  updates: BookingUpdate[];
};

export function BookingUpdates({ updates }: Props) {
  if (updates.length === 0) return null;

  return (
    <section className="panel">
      <h2 className="panel-title">Booking Updates</h2>
      <ul className="booking-list">
        {updates.map((update, idx) => (
          <li key={`${idx}-${update.status}-${update.message.slice(0, 12)}`} className={`booking-item booking-${update.status}`}>
            <p>{update.message}</p>
            {update.booking ? (
              <p className="booking-meta">
                {update.booking.doctorName} • {update.booking.displayLabel} • {update.booking.timezone}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

export type { BookingUpdate };
