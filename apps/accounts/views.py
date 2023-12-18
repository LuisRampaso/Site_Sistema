from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404, render, redirect
from accounts.forms import CustomUserCreationForm, UserChangeForm
from django.contrib.auth.models import Group, User
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from accounts.models import MyUser
from accounts.permission import grupo_colaborador_required
from config.utils import add_form_errors_to_messages
from core import settings
from user_profile.models import UserProfile 
from user_profile.forms import ProfileForm

from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

from django.core.mail import send_mail

# Create your views here.
def timeout_view(request):
    return render(request, 'accounts/timeout.html')

# Login
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            
            if user.is_authenticated and user.requires_password_change(): # Verifica
                msg = 'Olá'+user.first_name+', como você pode perceber atualmente \
                        a sua foi gerada automaticamente pelo sistema. Recomendamos fortemente \
                        que você altere sua senha para garantir a segurança da sua conta. \
                        É importante escolher uma senha forte e única que não seja fácil de adivinhar. \
                        Obrigado pela sua atenção!'
                messages.warning(request, msg)
                return redirect('force_password_change') # Rota de alterar a senha.
            else:
                return redirect('home')

        else:
            messages.error(request, 'Combinação de e-mail e senha inválida. \
                           Se o erro persistir entre em contato com o Adminstrador do sistema')

    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'accounts/login.html')

# Mudança de Senha Force (first_login)
@login_required
def force_password_change_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            user.force_change_password = False # passa o parametro para False.
            user.save()
            update_session_auth_hash(request, user)
            return redirect('password_change_done')
    else:
        form = PasswordChangeForm(request.user)
    context = {'form': form}
    return render(request, 'registration/password_force_change_form.html', context)

# Registro
def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST, user=request.user)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.is_valid = False
            usuario.is_active = False # Aprovação de registro pelo admin
            usuario.save()

            group = Group.objects.get(name='usuario')
            usuario.groups.add(group)

            # UserProfile.objects.create(usuario=usuario) # Cria instancia do perfil do usuário

            # Envia e-mail para usuário
            send_mail(
                'Cadastro Plataforma',
                f'Olá, {usuario.first_name}, em breve você receberá um e-mail de \
                    aprovação para usar a plataforma.',
                settings.DEFAULT_FROM_EMAIL, # De (em produção usar o e-mail que está no settings)
                [usuario.email], # para
                fail_silently = False
            )

            messages.success(request, 'Registrado. Um e-mail foi enviado \
                            para a adminstração aprovar. Aguarde contato.')
            return redirect('login')
            
            # messages.success(request, 'Registrado. Agora faça o login para começar!')
            # return redirect('login')
        else:
            form.data = form.data.copy()  # Copia os dados do formulário
            form.data['password'] = ''  # Limpa apenas o campo de senha
            add_form_errors_to_messages(request, form)
            

    form = CustomUserCreationForm(user=request.user)
    return render(request, "accounts/register.html",{"form": form})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required()
def update_my_user(request):
    if request.method == 'POST':
        user_form = UserChangeForm(request.POST, instance=request.user, user=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=request.user.perfil)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Seu perfil foi atualizado com sucesso!')
            return redirect('update-my-user')
        else:
            add_form_errors_to_messages(request, user_form)
            add_form_errors_to_messages(request, profile_form)
    else:
        user_form = UserChangeForm(instance=request.user, user=request.user)
        profile_form = ProfileForm(instance=request.user.perfil, user=request.user)

    return render(request, 'accounts/user_update.html', {'user_form': user_form, 'profile_form': profile_form})

@login_required()
@grupo_colaborador_required(['administrador','colaborador'])
def update_user(request, username):
    user = get_object_or_404(MyUser, username=username)
    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=user, user=request.user)
        if form.is_valid():
            usuario = form.save()

            if user.is_active: ## Se o usuário for ativado muda o status para True e envia o email
                usuario.is_active = True
                # Envia um Email informando o usuário
                send_mail( # Envia email para o usuário
                    'Cadastro Aprovado',
                    f"Olá, {usuario.first_name}, seu email foi aprovado na plataforma.",
                    settings.DEFAULT_FROM_EMAIL,
                    [usuario.email], # para
                    fail_silently=False,
                )
                messages.success(request, 'O usuário '+ usuario.email +'\
                                 foi atualizado com sucesso')
                return redirect('user_list')
            
            usuario.save()
            messages.success(request, ' O perfil de usuário foi atulizado com sucesso!')
            return redirect('user_list')
        
        else:
            add_form_errors_to_messages(request, form)
            
    else:
        form = UserChangeForm(instance=user, user=request.user)
    return render(request, 'accounts/user_update.html', {'form': form})

@login_required
@grupo_colaborador_required(['administrador','colaborador'])
def user_list(request): # Lista Cliente
    lista_usuarios = MyUser.objects.select_related('perfil').filter(is_superuser=False)
    return render(request, 'accounts/user_list.html', {'lista_usuarios': lista_usuarios})

'''@login_required
@grupo_colaborador_required(['administrador','colaborador'])
def add_user(request):
    user_form = CustomUserCreationForm(user=request.user)
    perfil_form = ProfileForm(user=request.user)

    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST, user=request.user)
        perfil_form = ProfileForm(request.POST, request.FILES, user=request.user)

        if user_form.is_valid() and perfil_form.is_valid():
            # Salve o usuário
            usuario = user_form.save()

            # Crie um novo perfil para o usuário
            perfil = perfil_form.save(commit=False)
            perfil.usuario = usuario
            perfil.save()
            messages.success(request, 'Usuário adicionado com sucesso.')
            return redirect('lista_usuarios')
        
    context = {'user_form': user_form, 'perfil_form': perfil_form}
    return render(request, "accounts/add-user.html", context)'''

@login_required
@grupo_colaborador_required(['administrador','colaborador'])
def add_user(request):
    user_form = CustomUserCreationForm(user=request.user)
    perfil_form = ProfileForm(user=request.user)

    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST, user=request.user)
        perfil_form = ProfileForm(request.POST, request.FILES, user=request.user)

        if user_form.is_valid() and perfil_form.is_valid():
            # Salve o usuário
            usuario = user_form.save()

            group = Group.objects.get(name='usuario')
            usuario.groups.add(group)

            # Crie um novo perfil para o usuário
            '''
            perfil = perfil_form.save(commit=False)
            perfil.usuario = user
            perfil.save()
            '''
            perfil, created = UserProfile.objects.get_or_create(usuario=usuario)
            perfil_form = ProfileForm(request.POST, request.FILES, instance=perfil, user=request.user)
            if perfil_form.is_valid():
                perfil_form.save()
            
            messages.success(request, 'Usuário adicionado com sucesso.')
            return redirect('user_list')
        else:
            # Verifica os erros para cada campo do formulário
            # Adicionar mensagens de erro aos campos dos formulários
            add_form_errors_to_messages(request, user_form)
            add_form_errors_to_messages(request, perfil_form)
            '''for field, error_list in user_form.errors.items():
                for error in error_list:
                    messages.error(request, f"Erro no campo '{user_form[field].label}': {error}")
            
            for field, error_list in perfil_form.errors.items():
                for error in error_list:
                    messages.error(request, f"Erro no campo '{user_form[field].label}': {error}")'''


        
    context = {'user_form': user_form, 'perfil_form': perfil_form}
    return render(request, "accounts/add-user.html", context)


