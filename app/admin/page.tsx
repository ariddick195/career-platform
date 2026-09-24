import { getProfileData } from "@/lib/db";

import {
  deleteItem,
  saveCertification,
  saveEducation,
  saveExperience,
  saveLink,
  saveProfile,
  saveProject,
  saveSkill,
  saveVolunteer,
} from "./actions";
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

export default function AdminPage() {
  const { person, education, experience, projects, skills, certifications, volunteers, links } =
    getProfileData();

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Admin</p>
          <h1>Career Platform Content Editor</h1>
        </div>
        <a href="/" className={styles.viewLink}>View public site</a>
      </header>

      <section className={styles.section}>
        <h2>Profile</h2>
        <form action={saveProfile} className={styles.formGrid}>
          <label>
            Full name
            <input name="fullName" defaultValue={display(person?.full_name)} />
          </label>
          <label>
            Location city
            <input name="locationCity" defaultValue={display(person?.location_city)} />
          </label>
          <label>
            Location state
            <input name="locationState" defaultValue={display(person?.location_state)} />
          </label>
          <label>
            Location country
            <input name="locationCountry" defaultValue={display(person?.location_country)} />
          </label>
          <label>
            Email
            <input name="email" defaultValue={display(person?.email)} />
          </label>
          <label>
            Phone
            <input name="phone" defaultValue={display(person?.phone)} />
          </label>
          <label className={styles.fullWidth}>
            Career goal
            <textarea name="careerGoal" defaultValue={display(person?.career_goal)} rows={3} />
          </label>
          <label className={styles.fullWidth}>
            Summary
            <textarea name="summary" defaultValue={display(person?.summary)} rows={3} />
          </label>
          <label className={styles.fullWidth}>
            Profile photo URL
            <input name="profilePhotoUrl" defaultValue={display(person?.profile_photo_url)} />
          </label>
          <button type="submit">Save profile</button>
        </form>
      </section>

      <section className={styles.section}>
        <h2>Education</h2>
        <div className={styles.list}>
          {education.map((item) => (
            <div key={item.id} className={styles.listItem}>
              <div>
                <strong>{display(item.institution_name)}</strong> — {display(item.degree_name)}
              </div>
              <form action={deleteItem}>
                <input type="hidden" name="entity" value="education" />
                <input type="hidden" name="id" value={String(item.id)} />
                <button type="submit" className={styles.deleteButton}>Delete</button>
              </form>
            </div>
          ))}
        </div>
        <form action={saveEducation} className={styles.formGrid}>
          <label>
            Institution
            <input name="institutionName" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            City
            <input name="city" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            State
            <input name="state" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Country
            <input name="country" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Start date
            <input name="startDate" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            End date
            <input name="endDate" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Degree
            <input name="degreeName" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Field of study
            <input name="fieldOfStudy" defaultValue="PLACEHOLDER" />
          </label>
          <label className={styles.fullWidth}>
            Relevant coursework
            <textarea name="relevantCoursework" rows={3} defaultValue="PLACEHOLDER" />
          </label>
          <button type="submit">Add education</button>
        </form>
      </section>

      <section className={styles.section}>
        <h2>Experience</h2>
        <div className={styles.list}>
          {experience.map((item) => (
            <div key={item.id} className={styles.listItem}>
              <div>
                <strong>{display(item.role_title)}</strong> at {display(item.company_name)}
              </div>
              <form action={deleteItem}>
                <input type="hidden" name="entity" value="experience" />
                <input type="hidden" name="id" value={String(item.id)} />
                <button type="submit" className={styles.deleteButton}>Delete</button>
              </form>
            </div>
          ))}
        </div>
        <form action={saveExperience} className={styles.formGrid}>
          <label>
            Company
            <input name="companyName" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Role title
            <input name="roleTitle" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            City
            <input name="city" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            State
            <input name="state" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Country
            <input name="country" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Start date
            <input name="startDate" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            End date
            <input name="endDate" defaultValue="PLACEHOLDER" />
          </label>
          <label className={styles.checkboxLabel}>
            <input type="checkbox" name="isCurrent" />
            Current role
          </label>
          <label className={styles.fullWidth}>
            Description
            <textarea name="description" rows={3} defaultValue="PLACEHOLDER" />
          </label>
          <label className={styles.fullWidth}>
            Achievements
            <textarea name="achievements" rows={5} defaultValue="PLACEHOLDER" />
          </label>
          <button type="submit">Add experience</button>
        </form>
      </section>

      <section className={styles.section}>
        <h2>Projects</h2>
        <div className={styles.list}>
          {projects.map((item) => (
            <div key={item.id} className={styles.listItem}>
              <div>
                <strong>{display(item.title)}</strong>
              </div>
              <form action={deleteItem}>
                <input type="hidden" name="entity" value="project" />
                <input type="hidden" name="id" value={String(item.id)} />
                <button type="submit" className={styles.deleteButton}>Delete</button>
              </form>
            </div>
          ))}
        </div>
        <form action={saveProject} className={styles.formGrid}>
          <label>
            Title
            <input name="title" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Category
            <input name="category" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Course name
            <input name="courseName" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Technologies used
            <input name="technologiesUsed" defaultValue="PLACEHOLDER" />
          </label>
          <label className={styles.fullWidth}>
            Description
            <textarea name="description" rows={4} defaultValue="PLACEHOLDER" />
          </label>
          <label className={styles.fullWidth}>
            Outcome
            <textarea name="outcome" rows={3} defaultValue="PLACEHOLDER" />
          </label>
          <label className={styles.fullWidth}>
            Project URL
            <input name="projectUrl" defaultValue="PLACEHOLDER" />
          </label>
          <button type="submit">Add project</button>
        </form>
      </section>

      <section className={styles.section}>
        <h2>Skills</h2>
        <div className={styles.list}>
          {skills.map((item) => (
            <div key={item.id} className={styles.listItem}>
              <div>
                <strong>{display(item.name)}</strong> — {display(item.category)}
              </div>
              <form action={deleteItem}>
                <input type="hidden" name="entity" value="skill" />
                <input type="hidden" name="id" value={String(item.id)} />
                <button type="submit" className={styles.deleteButton}>Delete</button>
              </form>
            </div>
          ))}
        </div>
        <form action={saveSkill} className={styles.formGrid}>
          <label>
            Skill name
            <input name="name" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Category
            <input name="category" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Proficiency level
            <input name="proficiencyLevel" defaultValue="PLACEHOLDER" />
          </label>
          <label className={styles.fullWidth}>
            Notes
            <textarea name="notes" rows={3} defaultValue="PLACEHOLDER" />
          </label>
          <button type="submit">Add skill</button>
        </form>
      </section>

      <section className={styles.section}>
        <h2>Certifications</h2>
        <div className={styles.list}>
          {certifications.map((item) => (
            <div key={item.id} className={styles.listItem}>
              <div>
                <strong>{display(item.name)}</strong>
              </div>
              <form action={deleteItem}>
                <input type="hidden" name="entity" value="certification" />
                <input type="hidden" name="id" value={String(item.id)} />
                <button type="submit" className={styles.deleteButton}>Delete</button>
              </form>
            </div>
          ))}
        </div>
        <form action={saveCertification} className={styles.formGrid}>
          <label>
            Certification name
            <input name="name" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Issuing organization
            <input name="issuingOrganization" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Completion date
            <input name="completionDate" defaultValue="PLACEHOLDER" />
          </label>
          <label className={styles.fullWidth}>
            Credential URL
            <input name="credentialUrl" defaultValue="PLACEHOLDER" />
          </label>
          <button type="submit">Add certification</button>
        </form>
      </section>

      <section className={styles.section}>
        <h2>Volunteer experience</h2>
        <div className={styles.list}>
          {volunteers.map((item) => (
            <div key={item.id} className={styles.listItem}>
              <div>
                <strong>{display(item.organization_name)}</strong>
              </div>
              <form action={deleteItem}>
                <input type="hidden" name="entity" value="volunteer" />
                <input type="hidden" name="id" value={String(item.id)} />
                <button type="submit" className={styles.deleteButton}>Delete</button>
              </form>
            </div>
          ))}
        </div>
        <form action={saveVolunteer} className={styles.formGrid}>
          <label>
            Organization
            <input name="organizationName" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Role title
            <input name="roleTitle" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Start date
            <input name="startDate" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            End date
            <input name="endDate" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Location
            <input name="location" defaultValue="PLACEHOLDER" />
          </label>
          <label className={styles.fullWidth}>
            Description
            <textarea name="description" rows={3} defaultValue="PLACEHOLDER" />
          </label>
          <button type="submit">Add volunteer experience</button>
        </form>
      </section>

      <section className={styles.section}>
        <h2>Links</h2>
        <div className={styles.list}>
          {links.map((item) => (
            <div key={item.id} className={styles.listItem}>
              <div>
                <strong>{display(item.label)}</strong> — {display(item.url)}
              </div>
              <form action={deleteItem}>
                <input type="hidden" name="entity" value="link" />
                <input type="hidden" name="id" value={String(item.id)} />
                <button type="submit" className={styles.deleteButton}>Delete</button>
              </form>
            </div>
          ))}
        </div>
        <form action={saveLink} className={styles.formGrid}>
          <label>
            Label
            <input name="label" defaultValue="PLACEHOLDER" />
          </label>
          <label>
            Category
            <input name="category" defaultValue="PLACEHOLDER" />
          </label>
          <label className={styles.fullWidth}>
            URL
            <input name="url" defaultValue="PLACEHOLDER" />
          </label>
          <button type="submit">Add link</button>
        </form>
      </section>
    </main>
  );
}
