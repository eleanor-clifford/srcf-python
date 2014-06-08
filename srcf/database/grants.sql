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
GRANT SELECT ON log TO sysadmins;
GRANT SELECT ON log_record_id_seq TO sysadmins;
