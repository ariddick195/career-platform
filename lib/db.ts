import fs from "fs";
import path from "path";
import Database from "better-sqlite3";

const dbDir = path.join(process.cwd(), "data");
const dbPath = path.join(dbDir, "career-platform.db");

function ensureDatabaseDirectory() {
  fs.mkdirSync(dbDir, { recursive: true });
}

function seedDefaultData(db: Database.Database) {
  const personCount = db
    .prepare("SELECT COUNT(*) as count FROM person")
    .get() as { count: number };

  if (personCount.count > 0) {
    return;
  }

  const personResult = db
    .prepare(
      `INSERT INTO person (
        full_name,
        location_city,
        location_state,
        location_country,
        email,
        phone,
        career_goal,
        summary,
        profile_photo_url
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .run(
      "Adam Riddick",
      "Los Angeles",
      "CA",
      "USA",
      "ariddick@lion.lmu.edu",
      "(424) 275-5352",
      "My career goal is to be a senior level logistics analyst or manager",
      "",
      ""
    ) as Database.RunResult;

  const personId = Number(personResult.lastInsertRowid);

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
    personId,
    "Loyola Marymount University",
    "Los Angeles",
    "CA",
    "PLACEHOLDER",
    "2023-08",
    "2027-05",
    "B.A.",
    "Information Systems and Business Analytics",
    "Analytics in Operations and Supply Chain Management; Programming for Business Applications; Database Management Systems"
  );

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
    personId,
    "LMU Distribution Center",
    "Los Angeles",
    "CA",
    "USA",
    "Shipping and Receiving Assistant",
    "2024-07",
    "Present",
    1,
    "Shipping and Receiving Assistant",
    "Processed an average of 250+ departmental orders weekly across nearly 200+ campus departments across 25 buildings with an error rate of approximately 0.02%.\nUtilized inventory software, Intra, to process and track orders, averaging approximately 50 departmental orders per hour during delivery operations.\nHandled peak-volume periods during campus move-in, processing up to 160 student packages per day over a 2-week span while maintaining organized tracking.\nTrained 6+ student hires on inventory software, order procedures, and delivery protocols.\nAssisted in evaluating linear, nonlinear, and modified time-tracking models to determine the most effective method for measuring employee package retrieval times."
  );

  const projectData = [
    {
      title: "Warehouse Location Optimization Analysis",
      category: "Academic / Analytics",
      course_name: "Analytics in Operations and Supply Chain Management",
      description:
        "Built an Excel Solver transportation cost minimization model comparing 2 potential warehouse locations across a network of 3 factories and 4 warehouse destinations with 400 units of demand, resulting in a $200 difference between the two.",
      technologies_used: "Excel Solver",
      outcome: "Compared two warehouse location options and identified a lower-cost option for the network.",
      project_url: "https://docs.google.com/spreadsheets/d/1rZb_5GI9rNmfYG8FWfZBDadpJeObkPxF/edit?gid=1498905323#gid=1498905323",
    },
    {
      title: "BMW Sales Graphs",
      category: "Academic / Data Visualization",
      course_name: "Programming for Business Applications",
      description:
        "Aggregated and visualized 15 years of BMW global sales data across 6 regions using pandas, Matplotlib, and NumPy to create comparative visualizations to identify regional sales patterns.",
      technologies_used: "pandas, Matplotlib, NumPy",
      outcome: "Created comparative region-level sales visualizations to highlight sales patterns.",
      project_url: "https://colab.research.google.com/drive/11UP45Bth57oH0uhtWMW0RvB_FpUAULgP",
    },
    {
      title: "Music Sales Database Analysis",
      category: "Academic / SQL",
      course_name: "Database Management Systems",
      description:
        "Created 13 SQL queries through various joins, aggregate functions, and subqueries against a multi-table music sales database to analyze sales and extract insights.",
      technologies_used: "SQL, MySQL",
      outcome: "Analyzed sales patterns and extracted business insights through database queries.",
      project_url: "https://github.com/ariddick195/Music-Sales-Database-Analysis/blob/main/Riddick%20SQL%20Assignment%209%20(1).sql",
    },
  ];

  for (const project of projectData) {
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
      personId,
      project.title,
      project.category,
      project.course_name,
      project.description,
      project.technologies_used,
      project.outcome,
      project.project_url
    );
  }

  const skills = [
    {
      name: "Excel & Access",
      category: "Tools",
      proficiency_level: "Strong",
      notes: "PivotTables, Solver, Data Analysis ToolPak, data cleaning, and database queries",
    },
    {
      name: "Supply Chain Analytics",
      category: "Domain",
      proficiency_level: "Strong",
      notes: "Cost, capacity, and volume optimization",
    },
    {
      name: "Inventory Management",
      category: "Domain",
      proficiency_level: "Strong",
      notes: "Inventory tracking, organization, and control",
    },
    {
      name: "Python",
      category: "Programming",
      proficiency_level: "Intermediate",
      notes: "Data ingestion, filtering, aggregation, and visualization",
    },
    {
      name: "MySQL",
      category: "Database",
      proficiency_level: "Intermediate",
      notes: "Data ingestion, filtering, aggregation, and visualization",
    },
  ];

  for (const skill of skills) {
    db.prepare(
      `INSERT INTO skill (person_id, name, category, proficiency_level, notes) VALUES (?, ?, ?, ?, ?)`
    ).run(
      personId,
      skill.name,
      skill.category,
      skill.proficiency_level,
      skill.notes
    );
  }

  const certifications = [
    "IBM Databases and SQL for Data Science with Python",
    "IBM Data Visualization and Dashboards with Excel and Cognos",
    "Microsoft Office Specialist: Excel Associate (Office 2019)",
  ];

  for (const name of certifications) {
    db.prepare(
      `INSERT INTO certification (person_id, name, issuing_organization, completion_date, credential_url) VALUES (?, ?, ?, ?, ?)`
    ).run(personId, name, "PLACEHOLDER", "PLACEHOLDER", "PLACEHOLDER");
  }

  const volunteerData = [
    {
      organization_name: "House of Yahweh Thrift Store",
      role_title: "Volunteer",
      start_date: "2022",
      end_date: "2022",
      location: "",
      description: "",
    },
    {
      organization_name: "Special Games for Individuals with Disabilities",
      role_title: "Volunteer",
      start_date: "2024",
      end_date: "2024",
      location: "",
      description: "",
    },
    {
      organization_name: "Greenworks Food Service",
      role_title: "Volunteer",
      start_date: "2024",
      end_date: "2024",
      location: "",
      description: "",
    },
  ];

  for (const volunteer of volunteerData) {
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
      personId,
      volunteer.organization_name,
      volunteer.role_title,
      volunteer.start_date,
      volunteer.end_date,
      volunteer.location,
      volunteer.description
    );
  }

  const links = [
    {
      label: "LinkedIn",
      url: "https://www.linkedin.com/in/adam-riddick-92750528a",
      category: "Professional",
    },
  ];

  for (const link of links) {
    db.prepare(
      `INSERT INTO link (person_id, label, url, category) VALUES (?, ?, ?, ?)`
    ).run(personId, link.label, link.url, link.category);
  }
}

ensureDatabaseDirectory();
const database = new Database(dbPath);
database.pragma("journal_mode = WAL");
database.exec(`
  CREATE TABLE IF NOT EXISTS person (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    location_city TEXT,
    location_state TEXT,
    location_country TEXT,
    email TEXT,
    phone TEXT,
    career_goal TEXT,
    summary TEXT,
    profile_photo_url TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS education (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    institution_name TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    start_date TEXT,
    end_date TEXT,
    degree_name TEXT,
    field_of_study TEXT,
    relevant_coursework TEXT,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (person_id) REFERENCES person(id)
  );

  CREATE TABLE IF NOT EXISTS experience (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    company_name TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    role_title TEXT,
    start_date TEXT,
    end_date TEXT,
    is_current INTEGER DEFAULT 0,
    description TEXT,
    achievements TEXT,
    FOREIGN KEY (person_id) REFERENCES person(id)
  );

  CREATE TABLE IF NOT EXISTS project (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    title TEXT,
    category TEXT,
    course_name TEXT,
    description TEXT,
    technologies_used TEXT,
    outcome TEXT,
    project_url TEXT,
    FOREIGN KEY (person_id) REFERENCES person(id)
  );

  CREATE TABLE IF NOT EXISTS skill (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    name TEXT,
    category TEXT,
    proficiency_level TEXT,
    notes TEXT,
    FOREIGN KEY (person_id) REFERENCES person(id)
  );

  CREATE TABLE IF NOT EXISTS certification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    name TEXT,
    issuing_organization TEXT,
    completion_date TEXT,
    credential_url TEXT,
    FOREIGN KEY (person_id) REFERENCES person(id)
  );

  CREATE TABLE IF NOT EXISTS volunteer_experience (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    organization_name TEXT,
    role_title TEXT,
    start_date TEXT,
    end_date TEXT,
    location TEXT,
    description TEXT,
    FOREIGN KEY (person_id) REFERENCES person(id)
  );

  CREATE TABLE IF NOT EXISTS link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    label TEXT,
    url TEXT,
    category TEXT,
    FOREIGN KEY (person_id) REFERENCES person(id)
  );
`);
seedDefaultData(database);

export type PersonRow = {
  id: number;
  full_name: string | null;
  location_city: string | null;
  location_state: string | null;
  location_country: string | null;
  email: string | null;
  phone: string | null;
  career_goal: string | null;
  summary: string | null;
  profile_photo_url: string | null;
};

export type EducationRow = {
  id: number;
  person_id: number;
  institution_name: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  start_date: string | null;
  end_date: string | null;
  degree_name: string | null;
  field_of_study: string | null;
  relevant_coursework: string | null;
};

export type ExperienceRow = {
  id: number;
  person_id: number;
  company_name: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  role_title: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: number;
  description: string | null;
  achievements: string | null;
};

export type ProjectRow = {
  id: number;
  person_id: number;
  title: string | null;
  category: string | null;
  course_name: string | null;
  description: string | null;
  technologies_used: string | null;
  outcome: string | null;
  project_url: string | null;
};

export type SkillRow = {
  id: number;
  person_id: number;
  name: string | null;
  category: string | null;
  proficiency_level: string | null;
  notes: string | null;
};

export type CertificationRow = {
  id: number;
  person_id: number;
  name: string | null;
  issuing_organization: string | null;
  completion_date: string | null;
  credential_url: string | null;
};

export type VolunteerRow = {
  id: number;
  person_id: number;
  organization_name: string | null;
  role_title: string | null;
  start_date: string | null;
  end_date: string | null;
  location: string | null;
  description: string | null;
};

export type LinkRow = {
  id: number;
  person_id: number;
  label: string | null;
  url: string | null;
  category: string | null;
};

export function getDatabase() {
  return database;
}

export function getProfileData(): {
  person: PersonRow | null;
  education: EducationRow[];
  experience: ExperienceRow[];
  projects: ProjectRow[];
  skills: SkillRow[];
  certifications: CertificationRow[];
  volunteers: VolunteerRow[];
  links: LinkRow[];
} {
  const person = database
    .prepare("SELECT * FROM person ORDER BY id ASC LIMIT 1")
    .get() as PersonRow | undefined;

  if (!person) {
    return {
      person: null,
      education: [],
      experience: [],
      projects: [],
      skills: [],
      certifications: [],
      volunteers: [],
      links: [],
    };
  }

  return {
    person,
    education: database
      .prepare("SELECT * FROM education WHERE person_id = ? ORDER BY start_date DESC")
      .all(Number(person.id)) as EducationRow[],
    experience: database
      .prepare("SELECT * FROM experience WHERE person_id = ? ORDER BY start_date DESC")
      .all(Number(person.id)) as ExperienceRow[],
    projects: database
      .prepare("SELECT * FROM project WHERE person_id = ? ORDER BY id ASC")
      .all(Number(person.id)) as ProjectRow[],
    skills: database
      .prepare("SELECT * FROM skill WHERE person_id = ? ORDER BY name ASC")
      .all(Number(person.id)) as SkillRow[],
    certifications: database
      .prepare("SELECT * FROM certification WHERE person_id = ? ORDER BY name ASC")
      .all(Number(person.id)) as CertificationRow[],
    volunteers: database
      .prepare("SELECT * FROM volunteer_experience WHERE person_id = ? ORDER BY start_date DESC")
      .all(Number(person.id)) as VolunteerRow[],
    links: database
      .prepare("SELECT * FROM link WHERE person_id = ? ORDER BY label ASC")
      .all(Number(person.id)) as LinkRow[],
  };
}
