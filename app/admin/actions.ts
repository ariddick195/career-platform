"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { getDatabase } from "@/lib/db";

function normalizeString(value: FormDataEntryValue | null | undefined) {
  const text = String(value ?? "").trim();
  return text === "" ? "PLACEHOLDER" : text;
}

export async function saveProfile(formData: FormData) {
  const db = getDatabase();
  const personId = 1;

  db.prepare(
    `UPDATE person SET
      full_name = ?,
      location_city = ?,
      location_state = ?,
      location_country = ?,
      email = ?,
      phone = ?,
      career_goal = ?,
      summary = ?,
      profile_photo_url = ?,
      updated_at = CURRENT_TIMESTAMP
    WHERE id = ?`
  ).run(
    normalizeString(formData.get("fullName")),
    normalizeString(formData.get("locationCity")),
    normalizeString(formData.get("locationState")),
    normalizeString(formData.get("locationCountry")),
    normalizeString(formData.get("email")),
    normalizeString(formData.get("phone")),
    normalizeString(formData.get("careerGoal")),
    normalizeString(formData.get("summary")),
    normalizeString(formData.get("profilePhotoUrl")),
    personId
  );

  revalidatePath("/");
  revalidatePath("/admin");
  redirect("/admin");
}

export async function saveEducation(formData: FormData) {
  const db = getDatabase();
  db.prepare(
    `INSERT INTO education (
      person_id,
      institution_name,
      city,
      state,
      country,
      start_date,
      end_date,
      degree_name,
      field_of_study,
      relevant_coursework
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  ).run(
    1,
    normalizeString(formData.get("institutionName")),
    normalizeString(formData.get("city")),
    normalizeString(formData.get("state")),
    normalizeString(formData.get("country")),
    normalizeString(formData.get("startDate")),
    normalizeString(formData.get("endDate")),
    normalizeString(formData.get("degreeName")),
    normalizeString(formData.get("fieldOfStudy")),
    normalizeString(formData.get("relevantCoursework"))
  );

  revalidatePath("/");
  revalidatePath("/admin");
  redirect("/admin");
}

export async function saveExperience(formData: FormData) {
  const db = getDatabase();
  db.prepare(
    `INSERT INTO experience (
      person_id,
      company_name,
      city,
      state,
      country,
      role_title,
      start_date,
      end_date,
      is_current,
      description,
      achievements
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
  ).run(
    1,
    normalizeString(formData.get("companyName")),
    normalizeString(formData.get("city")),
    normalizeString(formData.get("state")),
    normalizeString(formData.get("country")),
    normalizeString(formData.get("roleTitle")),
    normalizeString(formData.get("startDate")),
    normalizeString(formData.get("endDate")),
    formData.get("isCurrent") === "on" ? 1 : 0,
    normalizeString(formData.get("description")),
    normalizeString(formData.get("achievements"))
  );

  revalidatePath("/");
  revalidatePath("/admin");
  redirect("/admin");
}

export async function saveProject(formData: FormData) {
  const db = getDatabase();
  db.prepare(
    `INSERT INTO project (
      person_id,
      title,
      category,
      course_name,
      description,
      technologies_used,
      outcome,
      project_url
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
  ).run(
    1,
    normalizeString(formData.get("title")),
    normalizeString(formData.get("category")),
    normalizeString(formData.get("courseName")),
    normalizeString(formData.get("description")),
    normalizeString(formData.get("technologiesUsed")),
    normalizeString(formData.get("outcome")),
    normalizeString(formData.get("projectUrl"))
  );

  revalidatePath("/");
  revalidatePath("/admin");
  redirect("/admin");
}

export async function saveSkill(formData: FormData) {
  const db = getDatabase();
  db.prepare(
    `INSERT INTO skill (person_id, name, category, proficiency_level, notes) VALUES (?, ?, ?, ?, ?)`
  ).run(
    1,
    normalizeString(formData.get("name")),
    normalizeString(formData.get("category")),
    normalizeString(formData.get("proficiencyLevel")),
    normalizeString(formData.get("notes"))
  );

  revalidatePath("/");
  revalidatePath("/admin");
  redirect("/admin");
}

export async function saveCertification(formData: FormData) {
  const db = getDatabase();
  db.prepare(
    `INSERT INTO certification (person_id, name, issuing_organization, completion_date, credential_url) VALUES (?, ?, ?, ?, ?)`
  ).run(
    1,
    normalizeString(formData.get("name")),
    normalizeString(formData.get("issuingOrganization")),
    normalizeString(formData.get("completionDate")),
    normalizeString(formData.get("credentialUrl"))
  );

  revalidatePath("/");
  revalidatePath("/admin");
  redirect("/admin");
}

export async function saveVolunteer(formData: FormData) {
  const db = getDatabase();
  db.prepare(
    `INSERT INTO volunteer_experience (
      person_id,
      organization_name,
      role_title,
      start_date,
      end_date,
      location,
      description
    ) VALUES (?, ?, ?, ?, ?, ?, ?)`
  ).run(
    1,
    normalizeString(formData.get("organizationName")),
    normalizeString(formData.get("roleTitle")),
    normalizeString(formData.get("startDate")),
    normalizeString(formData.get("endDate")),
    normalizeString(formData.get("location")),
    normalizeString(formData.get("description"))
  );

  revalidatePath("/");
  revalidatePath("/admin");
  redirect("/admin");
}

export async function saveLink(formData: FormData) {
  const db = getDatabase();
  db.prepare(
    `INSERT INTO link (person_id, label, url, category) VALUES (?, ?, ?, ?)`
  ).run(
    1,
    normalizeString(formData.get("label")),
    normalizeString(formData.get("url")),
    normalizeString(formData.get("category"))
  );

  revalidatePath("/");
  revalidatePath("/admin");
  redirect("/admin");
}

export async function deleteItem(formData: FormData) {
  const entity = String(formData.get("entity") ?? "");
  const id = Number(formData.get("id") ?? "0");

  if (!entity || !id) {
    redirect("/admin");
  }

  const validTables: Record<string, string> = {
    education: "education",
    experience: "experience",
    project: "project",
    skill: "skill",
    certification: "certification",
    volunteer: "volunteer_experience",
    link: "link",
  };

  const table = validTables[entity];
  if (!table) {
    redirect("/admin");
  }

  const db = getDatabase();
  db.prepare(`DELETE FROM ${table} WHERE id = ?`).run(id);

  revalidatePath("/");
  revalidatePath("/admin");
  redirect("/admin");
}
