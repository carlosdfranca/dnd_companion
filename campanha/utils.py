def get_current_character(request):
    """
    Resolve o personagem atual. Hoje retorna o primeiro (uso solo).
    Futuramente: ler de request.session ou request.user.
    """
    from .models import Personagem
    pk = request.session.get("personagem_id")
    if pk:
        return Personagem.objects.filter(pk=pk).first() or Personagem.objects.first()
    return Personagem.objects.first()
