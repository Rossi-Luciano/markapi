from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'wagtailsearch_indexentry'
                      AND column_name = 'title_text'
                ) THEN
                    UPDATE wagtailsearch_indexentry
                    SET title_text = COALESCE(title_text, ''),
                        body_text = COALESCE(body_text, '');

                    ALTER TABLE wagtailsearch_indexentry
                        ALTER COLUMN title_text SET DEFAULT '',
                        ALTER COLUMN body_text SET DEFAULT '';
                END IF;
            END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
