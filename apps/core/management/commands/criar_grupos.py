"""
Comando para criar os grupos de acesso e usuários de teste.

Uso:
    python manage.py criar_grupos              # cria só os grupos
    python manage.py criar_grupos --com-usuarios  # cria grupos + usuários de teste
"""
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

GRUPOS = ["admin", "suporte", "colaborador"]

USUARIOS_TESTE = [
    {
        "username": "admin_teste",
        "email": "admin@krindges.local",
        "password": "Admin@123",
        "first_name": "Admin",
        "last_name": "Teste",
        "grupo": "admin",
        "is_staff": True,
    },
    {
        "username": "suporte_teste",
        "email": "suporte@krindges.local",
        "password": "Suporte@123",
        "first_name": "Suporte",
        "last_name": "Teste",
        "grupo": "suporte",
        "is_staff": False,
    },
    {
        "username": "colab_teste",
        "email": "colab@krindges.local",
        "password": "Colab@123",
        "first_name": "Colaborador",
        "last_name": "Teste",
        "grupo": "colaborador",
        "is_staff": False,
    },
]


class Command(BaseCommand):
    help = "Cria os grupos admin/suporte/colaborador e, opcionalmente, usuários de teste."

    def add_arguments(self, parser):
        parser.add_argument(
            "--com-usuarios",
            action="store_true",
            help="Cria também os usuários de teste para cada grupo.",
        )

    def handle(self, *args, **options):
        # 1. Garantir que todos os grupos existem
        for nome in GRUPOS:
            grupo, criado = Group.objects.get_or_create(name=nome)
            status = "criado" if criado else "já existia"
            self.stdout.write(f"  Grupo '{nome}': {status}")

        if not options["com_usuarios"]:
            self.stdout.write(self.style.SUCCESS("\nGrupos prontos. Use --com-usuarios para criar usuários de teste."))
            return

        self.stdout.write("")

        # 2. Criar usuários de teste
        for dados in USUARIOS_TESTE:
            username = dados["username"]
            grupo_obj = Group.objects.get(name=dados["grupo"])

            if User.objects.filter(username=username).exists():
                self.stdout.write(f"  Usuário '{username}': já existe (pulado)")
                continue

            user = User.objects.create_user(
                username=username,
                email=dados["email"],
                password=dados["password"],
                first_name=dados["first_name"],
                last_name=dados["last_name"],
                is_staff=dados["is_staff"],
            )
            user.groups.add(grupo_obj)

            self.stdout.write(
                self.style.SUCCESS(
                    f"  Usuário '{username}' criado  |  grupo: {dados['grupo']}  |  senha: {dados['password']}"
                )
            )

        self.stdout.write(self.style.SUCCESS("\nPronto!"))
