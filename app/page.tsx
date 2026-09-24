import { getProfileData, type LinkRow } from "@/lib/db";
import styles from "./page.module.css";

function display(value: unknown) {
  if (typeof value !== "string") {
    return "";
  }

  const trimmed = value.trim();
  if (!trimmed || trimmed === "PLACEHOLDER") {
    return "";
  }

  return trimmed;
}

export default function Home() {
  const { person, education, experience, projects, skills, certifications, volunteers, links } =
    getProfileData();

  const location = [person?.location_city, person?.location_state, person?.location_country]
    .filter(Boolean)
    .join(", ") || "PLACEHOLDER";

  const validLinks = links.filter(
    (link): link is LinkRow & { url: string } =>
      typeof link.url === "string" && link.url !== "PLACEHOLDER"
  );

  return (
    <main className={styles.page}>
      <header className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>Career profile</p>
          <h1>{display(person?.full_name)}</h1>
          <p className={styles.location}>{location}</p>
        </div>
        <div className={styles.contactCard}>
          <p>{display(person?.email)}</p>
          <p>{display(person?.phone)}</p>
          <a href="/admin">Manage content</a>
        </div>
      </header>

      <section className={styles.summarySection}>
        <div className={styles.sectionHeader}>
          <h2>Professional summary</h2>
        </div>
        <p className={styles.summaryText}>{display(person?.career_goal)}</p>
      </section>

      <section className={styles.contentSection}>
        <div className={styles.sectionHeader}>
          <h2>Education</h2>
        </div>
        <div className={styles.list}>
          {education.map((item) => (
            <article key={item.id} className={styles.itemCard}>
              <div className={styles.itemMeta}>
                <strong>{display(item.institution_name)}</strong>
                <span>
                  {display(item.city)}, {display(item.state)}
                </span>
              </div>
              <p className={styles.itemTitle}>
                {display(item.degree_name)} in {display(item.field_of_study)}
              </p>
              <p>
                {display(item.start_date)} – {display(item.end_date)}
              </p>
              <p>{display(item.relevant_coursework)}</p>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.contentSection}>
        <div className={styles.sectionHeader}>
          <h2>Experience</h2>
        </div>
        <div className={styles.list}>
          {experience.map((item) => (
            <article key={item.id} className={styles.itemCard}>
              <div className={styles.itemMeta}>
                <strong>{display(item.role_title)}</strong>
                <span>{display(item.company_name)}</span>
              </div>
              <p>
                {display(item.city)}, {display(item.state)}
              </p>
              <p>
                {display(item.start_date)} – {item.is_current ? "Present" : display(item.end_date)}
              </p>
              {display(item.description) ? <p>{display(item.description)}</p> : null}
              {display(item.achievements) ? (
                <ul className={styles.bulletList}>
                  {String(display(item.achievements))
                    .split("\n")
                    .filter(Boolean)
                    .map((achievement, index) => (
                      <li key={`${item.id}-${index}`}>{achievement}</li>
                    ))}
                </ul>
              ) : null}
            </article>
          ))}
        </div>
      </section>

      <section className={styles.contentSection}>
        <div className={styles.sectionHeader}>
          <h2>Projects</h2>
        </div>
        <div className={styles.list}>
          {projects.map((item) => (
            <article key={item.id} className={styles.itemCard}>
              <div className={styles.itemMeta}>
                <strong>{display(item.title)}</strong>
                <span>{display(item.category)}</span>
              </div>
              <p className={styles.itemTitle}>{display(item.course_name)}</p>
              <p>{display(item.description)}</p>
              <p>
                <strong>Tools:</strong> {display(item.technologies_used)}
              </p>
              <p>
                <strong>Outcome:</strong> {display(item.outcome)}
              </p>
              {item.project_url && item.project_url !== "PLACEHOLDER" ? (
                <a href={item.project_url ?? "#"} target="_blank" rel="noreferrer" className={styles.linkButton}>
                  View project
                </a>
              ) : null}
            </article>
          ))}
        </div>
      </section>

      <section className={styles.contentSection}>
        <div className={styles.sectionHeader}>
          <h2>Skills</h2>
        </div>
        <div className={styles.skillGrid}>
          {skills.map((skill) => (
            <div key={skill.id} className={styles.skillCard}>
              <h3>{display(skill.name)}</h3>
              <p>{display(skill.category)}</p>
              <p>{display(skill.proficiency_level)}</p>
              <small>{display(skill.notes)}</small>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.contentSection}>
        <div className={styles.sectionHeader}>
          <h2>Certifications</h2>
        </div>
        <ul className={styles.inlineList}>
          {certifications.map((item) => (
            <li key={item.id}>{display(item.name)}</li>
          ))}
        </ul>
      </section>

      <section className={styles.contentSection}>
        <div className={styles.sectionHeader}>
          <h2>Volunteer experience</h2>
        </div>
        <div className={styles.list}>
          {volunteers.map((item) => (
            <article key={item.id} className={styles.itemCard}>
              <div className={styles.itemMeta}>
                <strong>{display(item.organization_name)}</strong>
                <span>{display(item.role_title)}</span>
              </div>
              {(display(item.start_date) || display(item.end_date)) && (
                <p>
                  {display(item.start_date)}
                  {display(item.start_date) && display(item.end_date) ? " – " : ""}
                  {display(item.end_date)}
                </p>
              )}
              {display(item.location) ? <p>{display(item.location)}</p> : null}
              {display(item.description) ? <p>{display(item.description)}</p> : null}
            </article>
          ))}
        </div>
      </section>

      <section className={styles.contentSection}>
        <div className={styles.sectionHeader}>
          <h2>Links</h2>
        </div>
        <div className={styles.linkGrid}>
          {validLinks.map((link) => (
            <a key={link.id} href={link.url} target="_blank" rel="noreferrer" className={styles.linkButton}>
              {display(link.label)}
            </a>
          ))}
        </div>
      </section>
    </main>
  );
}
