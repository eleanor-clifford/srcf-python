-- root will be the owner of the database, so can read & write to everything
-- allow read only access to nobody (for srcf-who and the likes)
GRANT USAGE ON SCHEMA PUBLIC TO nobody;
GRANT SELECT (crsid, surname, preferred_name, email, joined, modified, member, "user") ON members TO nobody;
GRANT SELECT (society, description, joined, modified) ON societies TO nobody;
GRANT SELECT ON society_admins TO nobody;
