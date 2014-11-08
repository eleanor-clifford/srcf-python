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

CREATE FUNCTION jobs_trigger()
    RETURNS TRIGGER AS
    $$
        BEGIN
            IF NEW.state = 'queued' THEN
                PERFORM pg_notify('jobs_insert', NEW.job_id::text);
            END IF;
            RETURN NULL;
        END
    $$
    LANGUAGE plpgsql;

CREATE TRIGGER jobs_trigger
    AFTER INSERT OR UPDATE ON jobs
    FOR EACH ROW EXECUTE PROCEDURE jobs_trigger();
