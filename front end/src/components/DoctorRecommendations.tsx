import type { DoctorCard } from "../lib/liveSocket";

type Props = {
  symptomsSummary: string;
  doctors: DoctorCard[];
};

export function DoctorRecommendations({ symptomsSummary, doctors }: Props) {
  if (doctors.length === 0) return null;

  return (
    <section className="panel">
      <h2 className="panel-title">Recommended Doctors</h2>
      <p className="panel-subtitle">Based on: {symptomsSummary}</p>
      <div className="doctor-grid">
        {doctors.map((doctor) => (
          <article className="doctor-card" key={doctor.doctorId}>
            <div className="doctor-header">
              <h3>{doctor.name}</h3>
              <p>{doctor.specialty}</p>
            </div>
            <p className="doctor-meta">
              {doctor.experienceYears} years experience • {doctor.languages.join(", ")}
            </p>
            <p className="doctor-reason">{doctor.matchReason}</p>

            <h4 className="slots-title">Available slots</h4>
            <ul className="slot-list">
              {doctor.slots.map((slot) => (
                <li key={slot.slotId} className={slot.isAvailable ? "slot-item" : "slot-item slot-item-unavailable"}>
                  <span>{slot.displayLabel}</span>
                  <code>{slot.slotId}</code>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}
