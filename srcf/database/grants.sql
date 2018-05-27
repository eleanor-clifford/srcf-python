-- TODO: this is not up-to-date since the GDPR changes!

-- root will be the owner of the database, so can read & write to everything
-- allow read only access to nobody (for srcf-who and the likes)
GRANT USAGE ON SCHEMA PUBLIC TO nobody;
GRANT SELECT (crsid, surname, preferred_name, email, joined, modified, member, "user") ON members TO nobody;
GRANT SELECT (society, description, joined, modified) ON societies TO nobody;
GRANT SELECT ON society_admins TO nobody;

-- sysadmins uses pg_dump to back up the database
GRANT USAGE ON SCHEMA PUBLIC TO sysadmins;
GRANT SELECT ON members TO sysadmins;
GRANT SELECT ON societies TO sysadmins;
GRANT SELECT ON society_admins TO sysadmins;
GRANT SELECT ON pending_society_admins TO sysadmins;
GRANT SELECT ON log TO sysadmins;
GRANT SELECT ON log_record_id_seq TO sysadmins;
GRANT SELECT ON domains TO sysadmins;
GRANT SELECT ON domains_id_seq TO sysadmins;
GRANT SELECT ON jobs TO sysadmins;
GRANT SELECT ON job_log TO sysadmins;
GRANT SELECT ON job_log_log_id_seq TO sysadmins;
GRANT SELECT ON https_certs TO sysadmins;
GRANT SELECT ON https_certs_id_seq TO sysadmins;

-- the control webapp gets the priveleges of nobody, plus:
--     the ability to add jobs
--     the ability to see the danger flag
--     the ability to see pending admins
GRANT USAGE ON SCHEMA PUBLIC TO "srcf-admin";
GRANT SELECT (crsid, surname, preferred_name, email, joined, modified, member, "user", danger) ON members TO "srcf-admin";
GRANT SELECT (society, description, joined, modified, danger) ON societies TO "srcf-admin";
GRANT SELECT ON society_admins TO "srcf-admin";
GRANT SELECT ON pending_society_admins TO "srcf-admin";
GRANT SELECT ON domains TO "srcf-admin";
GRANT SELECT, INSERT ON jobs TO "srcf-admin";
GRANT SELECT, UPDATE ON jobs_job_id_seq TO "srcf-admin";
