# Railway Deployment

## Prerequisites
- Railway account at railway.app
- Railway CLI: `npm install -g @railway/cli`

## Deploy Steps

1. `railway login`
2. `railway init` (create new project)
3. Add PostgreSQL service in Railway dashboard → New → Database → PostgreSQL
4. Set environment variables in Railway dashboard:
   - `SECRET_KEY=<50-char random string>`
   - `DEBUG=False`
   - `ALLOWED_HOSTS=<your-app>.up.railway.app`
5. `railway up` (deploy)
6. `railway run python manage.py migrate`
7. `railway run python manage.py create_groups`
8. `railway run python manage.py createsuperuser`
9. Assign superuser to "Super Admin" group:
   ```
   railway run python manage.py shell -c "
   from django.contrib.auth.models import User, Group
   u = User.objects.get(username='<username>')
   u.groups.add(Group.objects.get(name='Super Admin'))
   "
   ```

## Verify

Open the Railway URL in a browser. Log in and confirm:
- Dashboard loads
- Can add Wilayah, Lingkungan, Member
- Can record a payment
- Reports export to Excel
