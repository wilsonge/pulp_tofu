from django.db import migrations, models
import django.db.models.deletion
import pulpcore.app.util


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0091_systemid'),
        ('core', '0106_alter_artifactdistribution_distribution_ptr_and_more')
    ]

    operations = [
        migrations.CreateModel(
            name='TofuPublication',
            fields=[
                ('publication_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.Publication')),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
            },
            bases=('core.publication',),
        ),
        migrations.CreateModel(
            name='TofuRemote',
            fields=[
                ('remote_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.Remote')),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
            },
            bases=('core.remote',),
        ),
        migrations.CreateModel(
            name='TofuRepository',
            fields=[
                ('repository_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.Repository')),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
            },
            bases=('core.repository',),
        ),
        migrations.CreateModel(
            name='Provider',
            fields=[
                ('content_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.Content')),
                ('namespace', models.TextField(help_text='The organization or user that publishes the provider')),
                ('type', models.TextField(help_text="The provider type (e.g., 'aws', 'azurerm', 'google', 'random')")),
                ('version', models.TextField(help_text='Semantic version number (semver 2.0)')),
                ('os', models.TextField(help_text="Operating system (e.g., 'linux', 'darwin', 'windows')")),
                ('arch', models.TextField(help_text="CPU architecture (e.g., 'amd64', 'arm', 'arm64')")),
                ('filename', models.TextField(help_text="The filename for this provider's zip archive")),
                ('shasum', models.CharField(db_index=True, max_length=64, help_text='SHA256 checksum for the provider package')),
                ('protocols', models.JSONField(default=list, help_text="Supported OpenTofu provider API versions (e.g., ['4.0', '5.1'])")),
                ('download_url', models.TextField(blank=True, null=True, help_text='The URL from which the provider package can be downloaded')),
                ('_pulp_domain', models.ForeignKey(default=pulpcore.app.util.get_domain_pk, on_delete=django.db.models.deletion.PROTECT, to='core.domain')),
            ],
            options={
                'default_related_name': '%(app_label)s_%(model_name)s',
                'unique_together': {('namespace', 'type', 'version', 'os', 'arch', '_pulp_domain')},
                'permissions': [
                    ("upload_provider_packages", "Can upload Provider packages using synchronous API."),
                ],
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
            bases=('core.distribution',),
        ),
    ]