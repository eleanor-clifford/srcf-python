CREATE FUNCTION set_joined() RETURNS TRIGGER AS $$
    BEGIN
        NEW.joined = now();
        RETURN NEW;
    END
$$ LANGUAGE plpgsql;

CREATE FUNCTION set_created() RETURNS TRIGGER AS $$
    BEGIN
        NEW.created = now();
        RETURN NEW;
    END
$$ LANGUAGE plpgsql;

CREATE FUNCTION set_modified() RETURNS TRIGGER AS $$
    BEGIN
        NEW.modified = now();
        RETURN NEW;
    END
$$ LANGUAGE plpgsql;

CREATE TRIGGER members_set_joined_trigger BEFORE INSERT ON members
    FOR EACH ROW EXECUTE PROCEDURE set_joined();
CREATE TRIGGER societies_set_joined_trigger BEFORE INSERT ON societies
    FOR EACH ROW EXECUTE PROCEDURE set_joined();

CREATE TRIGGER members_set_modified_trigger BEFORE INSERT OR UPDATE ON members
    FOR EACH ROW EXECUTE PROCEDURE set_modified();
CREATE TRIGGER societies_set_modified_trigger BEFORE INSERT OR UPDATE ON societies
    FOR EACH ROW EXECUTE PROCEDURE set_modified();

CREATE TRIGGER log_set_created_trigger BEFORE INSERT ON log
    FOR EACH ROW EXECUTE PROCEDURE set_created();
