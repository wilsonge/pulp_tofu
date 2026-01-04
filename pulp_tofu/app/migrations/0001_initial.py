import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    operations = [
        migrations.CreateModel(
            name='TofuPublication',
            fields=[
                ('publication_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='tofu_tofupublication', serialize=False, to='core.Publication')),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
            },
            bases=('core.publication',),
        ),
        migrations.CreateModel(
            name='TofuRemote',
            fields=[
                ('remote_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='tofu_tofuremote', serialize=False, to='core.Remote')),
                ('includes', models.JSONField(default=list)),
                ('excludes', models.JSONField(default=list)),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
            },
            bases=('core.remote',),
        ),
        migrations.CreateModel(
            name='TofuRepository',
            fields=[
                ('repository_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='tofu_tofurepository', serialize=False, to='core.Repository')),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
            },
            bases=('core.repository',),
        ),
        migrations.CreateModel(
            name='Provider',
            fields=[
                ('content_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='tofu_provider', serialize=False, to='core.Content')),
                ('version', models.TextField()),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
                'unique_together': {},
            },
            bases=('core.content',),
        ),
        migrations.CreateModel(
            name='TofuDistribution',
            fields=[
                ('distribution_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.distribution')),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
            },
            bases=('core.basedistribution',),
        ),
    ]