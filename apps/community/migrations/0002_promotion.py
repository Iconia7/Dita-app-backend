# Generated manually by DITA AI on 2026-04-04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Promotion',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('title', models.CharField(max_length=100)),
                        ('description', models.TextField()),
                        ('image', models.ImageField(blank=True, null=True, upload_to='promotions/')),
                        ('link', models.URLField(blank=True, null=True)),
                        ('is_active', models.BooleanField(default=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                    ],
                ),
            ],
            database_operations=[
                # If table doesn't exist, create it. If it does, just add the missing column.
                migrations.RunSQL(
                    sql="""
                    CREATE TABLE IF NOT EXISTS community_promotion (
                        id bigserial PRIMARY KEY,
                        title varchar(100) NOT NULL,
                        image varchar(100),
                        link varchar(200),
                        is_active boolean NOT NULL DEFAULT true,
                        created_at timestamptz NOT NULL
                    );
                    ALTER TABLE community_promotion ADD COLUMN IF NOT EXISTS description text;
                    """,
                    reverse_sql="DROP TABLE IF EXISTS community_promotion;"
                ),
            ],
        ),
    ]
