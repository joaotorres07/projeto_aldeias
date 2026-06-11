from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
from reportlab.lib.colors import HexColor, black, grey
import os


def _s(val):
    """Retorna string segura para o PDF."""
    if val is None:
        return ""
    return str(val).strip()


def _sim_nao(val):
    if val == "sim":
        return "<b>Sim</b>"
    elif val == "nao":
        return "<b>Não</b>"
    return ""


def _radio(val, opcoes):
    """Retorna apenas o label da opção selecionada."""
    for v, label in opcoes:
        if val == v:
            return f"<b>{label}</b>"
    return ""


def gerar_pdf_entrevista(d):
    """Gera PDF da ficha de entrevista. Recebe dict com dados do formulário. Retorna BytesIO."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleCustom', parent=styles['Title'], fontSize=13, leading=16,
                                  alignment=TA_CENTER, spaceAfter=2, textColor=black)
    subtitle_style = ParagraphStyle('SubtitleCustom', parent=styles['Normal'], fontSize=10, leading=13,
                                     alignment=TA_CENTER, spaceAfter=4, textColor=black)
    section_style = ParagraphStyle('SectionCustom', parent=styles['Heading2'], fontSize=11, leading=14,
                                    spaceBefore=12, spaceAfter=4, textColor=HexColor('#2d3748'),
                                    borderWidth=0, underline=True)
    normal = ParagraphStyle('NormalCustom', parent=styles['Normal'], fontSize=9, leading=12, alignment=TA_LEFT)
    normal_just = ParagraphStyle('NormalJust', parent=styles['Normal'], fontSize=9, leading=12, alignment=TA_JUSTIFY)
    bold_style = ParagraphStyle('BoldCustom', parent=normal, fontName='Helvetica-Bold')
    small = ParagraphStyle('SmallCustom', parent=normal, fontSize=8, leading=10, textColor=grey)
    obs_style = ParagraphStyle('ObsCustom', parent=styles['Normal'], fontSize=8, leading=10,
                                alignment=TA_CENTER, textColor=HexColor('#cc0000'))

    elements = []

    # ==================== CABEÇALHO ====================
    # Logo/ícone centralizado acima do título
    logo_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'img', 'iconeAldeias.jpeg')
    if os.path.exists(logo_path):
        try:
            logo_img = RLImage(logo_path, width=25 * mm, height=25 * mm)
            logo_img.hAlign = 'CENTER'
            elements.append(logo_img)
            elements.append(Spacer(1, 2 * mm))
        except Exception:
            pass

    sexo = _s(d.get('sexo'))

    num_aldeia = _s(d.get('num_aldeia'))
    tipo_aldeia_nome = _s(d.get('tipo_aldeia_nome')) or 'ALDEIA DE APROFUNDAMENTO'
    nucleo_aldeia_nome = _s(d.get('nucleo_aldeia_nome')) or ''

    titulo_aldeia = f"{num_aldeia}ª {tipo_aldeia_nome.upper()}" if num_aldeia else tipo_aldeia_nome.upper()
    if nucleo_aldeia_nome:
        titulo_aldeia += f" DE {nucleo_aldeia_nome.upper()}"

    elements.append(Paragraph(titulo_aldeia, title_style))
    elements.append(Paragraph("ALDEIAS DE VIDA – IDADE MÍNIMA 19 ANOS", subtitle_style))

    datas_aldeia = _s(d.get('datas_aldeia'))
    elements.append(Paragraph(f"INSCRIÇÃO PESSOAL PARA ALDEIA DOS DIAS: {datas_aldeia}", subtitle_style))
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph('"FAVOR DEVOLVER ESTA FICHA EM CASO DE DESISTÊNCIA"', obs_style))
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(
        "NÃO SE ASSUSTE COM O TAMANHO DE NOSSA FICHA, É PARA MELHOR NOS CONHECERMOS E "
        "PARA QUE POSSAMOS MELHOR LHE AJUDAR. PEDIMOS QUE PREENCHA AS PERGUNTAS ABAIXO "
        "DA MELHOR FORMA QUE PUDER.", small))
    elements.append(Spacer(1, 4 * mm))

    # ==================== DADOS PESSOAIS ====================
    elements.append(Paragraph("<u><b>DADOS PESSOAIS</b></u>", section_style))

    def _field(label, value, width_pct=None):
        v = _s(value)
        return f"<b>{label}:</b> {v}"

    def _line(*parts):
        text = "&nbsp;&nbsp;&nbsp;&nbsp;".join(parts)
        elements.append(Paragraph(text, normal))
        elements.append(Spacer(1, 1.5 * mm))

    _line(_field("Nome completo", d.get('nome_completo')),
          f"<b>Sexo:</b> {sexo}")

    # Formatar data de nascimento para dd/mm/yyyy
    data_nasc_raw = _s(d.get('data_nascimento'))
    data_nasc_fmt = data_nasc_raw
    if data_nasc_raw and '-' in data_nasc_raw:
        try:
            parts = data_nasc_raw.split('-')
            data_nasc_fmt = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass

    _line(_field("Apelido", d.get('apelido')),
          _field("Data de Nascimento", data_nasc_fmt),
          _field("Idade", d.get('idade')))
    _line(_field("Endereço", d.get('endereco')),
          _field("Nº", d.get('endereco_num')),
          _field("Aptº", d.get('endereco_apto')))
    _line(_field("Ponto de referência", d.get('ponto_referencia')),
          _field("Bairro", d.get('bairro')),
          _field("Cidade", d.get('cidade')))
    _line(_field("Estado", d.get('estado')),
          _field("CEP", d.get('cep')),
          _field("Tipo Sanguíneo", d.get('tipo_sanguineo')),
          _field("Tel Res.", d.get('tel_residencial')))
    _line(_field("Celular/WhatsApp", d.get('celular_whatsapp')))
    _line(_field("Email", d.get('email')),
          _field("Profissão", d.get('profissao')))
    _line(_field("Qual sua Religião", d.get('religiao')),
          _field("Se católico, há quanto tempo não se confessa", d.get('tempo_confissao')))

    estado_civil = _s(d.get('estado_civil'))
    ec_opcoes = [('solteiro', 'Solteiro(a)'), ('casado', 'Casado(a)'), ('divorciado', 'Divorciado(a)'),
                 ('amasiado', 'Amasiado(a)'), ('viuvo', 'Viúvo(a)')]
    _line(f"<b>Você é:</b> {_radio(estado_civil, ec_opcoes)}")

    esta_gravida = _s(d.get('esta_gravida'))
    sexo_val = _s(d.get('sexo'))
    if sexo_val != 'M':
        _line(f"<b>Está Grávida?</b> {_sim_nao(esta_gravida)}")

        elements.append(Paragraph(
            "<b>OBS.: caso esteja grávida, aguarde uma próxima oportunidade para participar da aldeia.</b>",
            ParagraphStyle('ObsGravida', parent=normal, textColor=HexColor('#cc0000'), fontName='Helvetica-Bold')))
        elements.append(Spacer(1, 1.5 * mm))

    _line(_field("Através de quem você está vindo para a aldeia", d.get('atraves_de_quem')))

    tem_filhos = _s(d.get('tem_filhos'))
    _line(f"<b>Você tem filhos?</b> {_sim_nao(tem_filhos)}")
    if tem_filhos == 'sim':
        _line(_field("Quantos", d.get('quantos_filhos')))
        _line(_field("Nome e idade dos filhos", d.get('nome_idade_filhos')))

    # ==================== CÔNJUGE (somente se casado/amasiado) ====================
    if estado_civil in ('casado', 'amasiado'):
        elements.append(Spacer(1, 2 * mm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=grey))
        elements.append(Paragraph("<u><b>CÔNJUGE</b></u>", section_style))

        _line(_field("É casado(a) há quanto tempo", d.get('tempo_casado')),
              _field("Nome do(a) seu Esposo(a)", d.get('nome_esposo')))
        _line(_field("Religião do(a) cônjuge", d.get('religiao_conjuge')))
        _line(_field("O que ele(a) acha de você fazer a Aldeia de Vida", d.get('opiniao_conjuge')))

    # ==================== PAIS ====================
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=grey))
    elements.append(Paragraph("<u><b>PAIS</b></u>", section_style))

    mora_pais = _s(d.get('mora_com_pais'))
    _line(f"<b>Você vive com seus pais?</b> {_sim_nao(mora_pais)}")

    vivo_com = _s(d.get('vivo_com'))
    if mora_pais == 'sim' and vivo_com:
        vc_opcoes = [('mae', 'Mãe'), ('pai', 'Pai'), ('ambos', 'Ambos')]
        _line(f"<b>Vivo com:</b> {_radio(vivo_com, vc_opcoes)}")

    pai_status = _s(d.get('pai_status'))
    pai_opcoes = [('vivo', 'Vivo'), ('falecido', 'Falecido'), ('sem_relacionamento', 'Sem relacionamento')]
    if pai_status != 'sem_relacionamento':
        _line(_field("Nome do Pai", d.get('nome_pai')),
              f"  {_radio(pai_status, pai_opcoes)}")
    else:
        _line(f"<b>Pai:</b> {_radio(pai_status, pai_opcoes)}")

    mae_status = _s(d.get('mae_status'))
    mae_opcoes = [('viva', 'Viva'), ('falecida', 'Falecida'), ('sem_relacionamento', 'Sem relacionamento')]
    if mae_status != 'sem_relacionamento':
        _line(_field("Nome da Mãe", d.get('nome_mae')),
              f"  {_radio(mae_status, mae_opcoes)}")
    else:
        _line(f"<b>Mãe:</b> {_radio(mae_status, mae_opcoes)}")

    pais_casados = _s(d.get('pais_casados'))
    pc_opcoes = [('sim', 'Sim'), ('nao', 'Não'), ('divorciados', 'Divorciados')]
    _line(f"<b>Seus pais são Casados?</b> {_radio(pais_casados, pc_opcoes)}")

    vivem_juntos = _s(d.get('vivem_juntos'))
    _line(f"<b>Vivem juntos?</b> {_sim_nao(vivem_juntos)}")

    pai_disponivel = pai_status not in ('falecido', 'sem_relacionamento')
    mae_disponivel = mae_status not in ('falecida', 'sem_relacionamento')

    if pai_disponivel:
        _line(_field("Qual a religião do seu Pai", d.get('religiao_pai')),
              _field("Telefone do Pai", d.get('telefone_pai')))
    if mae_disponivel:
        _line(_field("Qual a religião de sua Mãe", d.get('religiao_mae')),
              _field("Telefone da Mãe", d.get('telefone_mae')))

    elements.append(Spacer(1, 1.5 * mm))
    elements.append(Paragraph(
        "Se você <b>NÃO MORA</b> com seus pais coloque o endereço deles:", normal))
    elements.append(Spacer(1, 1.5 * mm))

    # Endereços dos pais: conjunto ou separados
    # Se vivo_com é ambos, mostrar endereço conjunto independente do status falecido
    if vivem_juntos == 'sim' and (vivo_com == 'ambos' or (pai_disponivel and mae_disponivel)):
        _line(_field("Endereço dos Pais", d.get('endereco_pais')),
              _field("Nº", d.get('endereco_pais_num')),
              _field("Bairro", d.get('bairro_pais')))
        _line(_field("Cidade", d.get('cidade_pais')),
              _field("Estado", d.get('estado_pais')))
    else:
        if pai_disponivel:
            _line(_field("Endereço do pai", d.get('endereco_pai')),
                  _field("Nº", d.get('endereco_pai_num')),
                  _field("Bairro", d.get('bairro_pai')))
            _line(_field("Cidade", d.get('cidade_pai')),
                  _field("Estado", d.get('estado_pai')))
        if mae_disponivel:
            _line(_field("Endereço da mãe", d.get('endereco_mae')),
                  _field("Nº", d.get('endereco_mae_num')),
                  _field("Bairro", d.get('bairro_mae')))
            _line(_field("Cidade", d.get('cidade_mae')),
                  _field("Estado", d.get('estado_mae')))

    # ==================== OUTRAS INFORMAÇÕES ====================
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=grey))
    elements.append(Paragraph("<u><b>OUTRAS INFORMAÇÕES IMPORTANTES</b></u>", section_style))

    doenca = _s(d.get('doenca_cronica'))
    _line(f"<b>Tem alguma doença crônica ou é alérgica?</b> {_sim_nao(doenca)}")
    if doenca == 'sim':
        _line(_field("A quê", d.get('doenca_qual')))

    faz_tratamento = _s(d.get('faz_tratamento'))
    _line(f"<b>Faz algum tratamento?</b> {_sim_nao(faz_tratamento)}")
    if faz_tratamento == 'sim':
        _line(_field("Qual", d.get('tratamento')))

    toma_remedio = _s(d.get('toma_remedio'))
    _line(f"<b>Você toma algum remédio regularmente?</b> {_sim_nao(toma_remedio)}")
    if toma_remedio == 'sim':
        _line(_field("Qual", d.get('remedio')))

    agressiva = _s(d.get('agressiva'))
    depressiva = _s(d.get('depressiva'))
    _line(f"<b>Você é uma pessoa agressiva?</b> {_sim_nao(agressiva)}",
          f"    <b>Você é depressiva?</b> {_sim_nao(depressiva)}")

    problema_fisico = _s(d.get('problema_fisico'))
    _line(f"<b>Você tem algum problema que lhe impeça de caminhar, correr, pular, subir morro etc.?</b> {_sim_nao(problema_fisico)}")

    acomp_psico = _s(d.get('acompanhamento_psicologico'))
    ap_opcoes = [('ja_fiz', 'Já Fiz'), ('faco', 'Faço'), ('nunca_fiz', 'Nunca fiz')]
    _line(f"<b>Já fez algum acompanhamento psicológico?</b> {_radio(acomp_psico, ap_opcoes)}")

    vicio_drogas = _s(d.get('vicio_drogas'))
    _line(f"<b>Você já teve ou tem algum vício com Drogas?</b> {_sim_nao(vicio_drogas)}")

    bebida = _s(d.get('bebida_alcoolica'))
    _line(f"<b>Você faz uso de bebida alcoólica?</b> {_sim_nao(bebida)}")
    if bebida == 'sim':
        viciado = _s(d.get('viciado_bebida'))
        _line(f"<b>É viciado nesta bebida?</b> {_sim_nao(viciado)}")

    fuma = _s(d.get('fuma'))
    _line(f"<b>Você fuma?</b> {_sim_nao(fuma)}")
    if fuma == 'sim':
        consegue_sem_fumar = _s(d.get('consegue_sem_fumar'))
        _line(f"<b>Consegue ficar 3 dias sem fumar?</b> {_sim_nao(consegue_sem_fumar)}")

    familia_aldeia = _s(d.get('familia_fez_aldeia'))
    _line(f"<b>Alguém de sua família já fez aldeia?</b> {_sim_nao(familia_aldeia)}")
    if familia_aldeia == 'sim':
        _line(_field("Quem", d.get('familia_aldeia_quem')))

    participante = _s(d.get('participante_aldeia'))
    _line(f"<b>Algum parente, amigo(a), namorado(a), vai participar desta aldeia?</b> {_sim_nao(participante)}")
    if participante == 'sim':
        _line(_field("Nome e grau de parentesco", d.get('participante_detalhe')))

    batizado = _s(d.get('batizado'))
    primeira_comunhao = _s(d.get('primeira_comunhao'))
    crismado = _s(d.get('crismado'))
    _line(f"<b>Você foi: Batizado(a)?</b> {_sim_nao(batizado)}",
          f"  <b>Fez a Primeira Comunhão?</b> {_sim_nao(primeira_comunhao)}",
          f"  <b>Crismado(a)?</b> {_sim_nao(crismado)}")

    sacramento = _s(d.get('gostaria_sacramento'))
    _line(f"<b>Se você não fez, gostaria de fazer algum dos Sacramentos?</b> {_sim_nao(sacramento)}")

    # ==================== PERGUNTAS PESSOAIS ====================
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=grey))
    elements.append(Paragraph("<u><b>PERGUNTAS PESSOAIS</b></u>", section_style))

    perguntas = [
        ("Quais são os seus maiores sonhos", d.get('maiores_sonhos')),
        ("Qual é a pessoa com quem você melhor se relaciona", d.get('melhor_relaciona')),
        ("Qual é a pessoa humana mais importante na sua vida hoje", d.get('pessoa_importante')),
        ("Quais são hoje os seus maiores problemas", d.get('maiores_problemas')),
        ("Qual é a pessoa com quem você tem maior dificuldade de relacionamento", d.get('dificuldade_relacionamento')),
        ("Qual a origem dessa dificuldade", d.get('origem_dificuldade')),
        ("Porque você deseja fazer a Aldeia de Aprofundamento", d.get('porque_aldeia')),
    ]
    for label, val in perguntas:
        v = _s(val)
        elements.append(Paragraph(f"<b>{label}?</b>", normal))
        elements.append(Paragraph(v, normal_just))
        elements.append(Spacer(1, 2 * mm))

    # ==================== INFORMAÇÃO ADICIONAL ====================
    elements.append(Spacer(1, 2 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=grey))
    elements.append(Paragraph("<u><b>INFORMAÇÃO ADICIONAL</b></u>", section_style))
    elements.append(Paragraph(
        "<b>Você tem mais alguma informação importante sobre você, para que melhor possamos lhe ajudar?</b>", normal))
    elements.append(Spacer(1, 1.5 * mm))
    elements.append(Paragraph(_s(d.get('info_adicional')), normal_just))

    # ==================== EMERGÊNCIA ====================
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=grey))
    elements.append(Paragraph("<u><b>EM CASO DE EMERGÊNCIA QUEM VOCÊ GOSTARIA QUE CHAMASSE?</b></u>", section_style))

    for i in range(1, 3):
        prefix = f"emerg{i}_"
        _line(_field("Nome", d.get(f'{prefix}nome')),
              _field("Telefone", d.get(f'{prefix}telefone')),
              _field("Parentesco", d.get(f'{prefix}parentesco')))
        _line(_field("Endereço", d.get(f'{prefix}endereco')),
              _field("N.º", d.get(f'{prefix}num')),
              _field("Bairro", d.get(f'{prefix}bairro')),
              _field("Cidade", d.get(f'{prefix}cidade')))
        if i == 1:
            elements.append(Spacer(1, 1.5 * mm))

    # ==================== CONTRIBUIÇÃO ====================
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=grey))
    elements.append(Paragraph("<u><b>CONTRIBUIÇÃO</b></u>", section_style))

    elements.append(Paragraph(
        "Contribuição para a minha alimentação, transporte e outras despesas durante a Aldeia.", normal))
    elements.append(Spacer(1, 2 * mm))

    ira_contribuir = _s(d.get('ira_contribuir'))
    _line(f"<b>Irá fazer contribuição?</b> {_sim_nao(ira_contribuir)}")

    if ira_contribuir == 'sim':
        contribuiu = _s(d.get('contribuiu_entrevista'))
        _line(f"<b>Contribuiu no dia da entrevista?</b> {_sim_nao(contribuiu)}")

        if contribuiu == 'sim':
            _line(_field("Qual valor? R$", d.get('valor_contribuicao')))
        else:
            _line(_field("Vai contribuir até o dia", d.get('data_contribuicao_futura')),
                  _field("Qual valor? R$", d.get('valor_contribuicao_futura')))

    # ==================== ATO DE COMPROMISSO ====================
    elements.append(Spacer(1, 6 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=grey))
    elements.append(Paragraph("<u><b>ATO DE COMPROMISSO COM AS ALDEIAS DE VIDA</b></u>",
                              ParagraphStyle('AtoTitle', parent=section_style, alignment=TA_CENTER)))

    nome_completo = _s(d.get('nome_completo'))
    num_aldeia_txt = _s(d.get('num_aldeia'))
    datas_aldeia_txt = _s(d.get('datas_aldeia'))
    tipo_aldeia_txt = _s(d.get('tipo_aldeia_nome')) or 'ALDEIA DE APROFUNDAMENTO'

    compromisso_text = (
        f"Eu <b>{nome_completo}</b>, comprometo-me ocupar a vaga para a {num_aldeia_txt}ª "
        f"{tipo_aldeia_txt.upper()}, que acontecerá no(s) dia(s) <b>{datas_aldeia_txt}</b>, participar de todos "
        "os momentos propostos pela Aldeia e cumprir o regulamento interno a ser apresentado na abertura da "
        "mesma. Comprometo-me também a levar comigo a lista de material necessário para esta Aldeia, "
        "contribuindo com a quantia de R$ 200,00 (duzentos reais) ou outra quantia, caso você possa dar uma "
        "contribuição maior a fim de ajudar outras pessoas que não podem contribuir."
    )
    elements.append(Paragraph(compromisso_text, normal_just))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        "Autorizo também, a Associação Aldeias de Vida, utilizar se necessário o uso de minha imagem (fotos e "
        "filmagem) e a publicação de minha partilha do mural desta aldeia.", normal_just))
    elements.append(Spacer(1, 6 * mm))

    elements.append(Paragraph(
        f"Belo Horizonte-MG, ____/____/_______, Aldeeiro(a): ___________________________________", normal))

    # ==================== OBSERVAÇÕES DO ENTREVISTADOR ====================
    elements.append(Spacer(1, 6 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=grey))
    elements.append(Paragraph("<u><b>(PREENCHIMENTO OBRIGATÓRIO PELO ENTREVISTADOR)</b></u>", section_style))
    elements.append(Paragraph("<b>Observações:</b>", normal))
    elements.append(Spacer(1, 2 * mm))

    obs_text = _s(d.get('observacoes_entrevistador'))
    for line in obs_text.split('\n'):
        elements.append(Paragraph(line, normal))
        elements.append(Spacer(1, 1.5 * mm))

    elements.append(Spacer(1, 8 * mm))
    entrevistador = _s(d.get('nome_entrevistador')) or '________________________________'
    entrevistador_tel = _s(d.get('telefone_entrevistador')) or '________________'
    entrevistador_data_raw = _s(d.get('data_entrevista'))
    entrevistador_data = entrevistador_data_raw
    if entrevistador_data_raw and '-' in entrevistador_data_raw:
        try:
            parts = entrevistador_data_raw.split('-')
            entrevistador_data = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass
    elements.append(Paragraph(
        f"<b>Entrevistador(a):</b> {entrevistador}; Belo Horizonte, {entrevistador_data}  "
        f"Tel: {entrevistador_tel}", normal))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def gerar_pdf_ficha_visitacao(d):
    """Gera PDF da Ficha de Visitação (Relatório da Entrevista para a Coordenação da Visitação).
    Recebe dict com dados do formulário. Retorna BytesIO."""

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm
    )

    styles = getSampleStyleSheet()
    # Estilos
    title_style = ParagraphStyle('FVTitle', parent=styles['Title'], fontSize=14, leading=17,
                                  alignment=TA_CENTER, spaceAfter=2, textColor=black,
                                  fontName='Helvetica-Bold')
    subtitle_style = ParagraphStyle('FVSubtitle', parent=styles['Normal'], fontSize=10, leading=13,
                                     alignment=TA_CENTER, spaceAfter=2, textColor=black,
                                     fontName='Helvetica-Bold')
    intro_style = ParagraphStyle('FVIntro', parent=styles['Normal'], fontSize=8, leading=10,
                                  alignment=TA_LEFT, textColor=black,
                                  fontName='Helvetica-BoldOblique')
    cell_label = ParagraphStyle('FVCellLabel', parent=styles['Normal'], fontSize=7.5, leading=9,
                                 alignment=TA_LEFT, textColor=HexColor('#333333'),
                                 fontName='Helvetica')
    cell_value = ParagraphStyle('FVCellValue', parent=styles['Normal'], fontSize=9, leading=11,
                                 alignment=TA_LEFT, textColor=black,
                                 fontName='Helvetica-Bold')
    cell_small = ParagraphStyle('FVCellSmall', parent=styles['Normal'], fontSize=7, leading=9,
                                 alignment=TA_LEFT, textColor=HexColor('#555555'),
                                 fontName='Helvetica')
    cabana_style = ParagraphStyle('FVCabana', parent=styles['Normal'], fontSize=8, leading=10,
                                   alignment=TA_LEFT, textColor=black,
                                   fontName='Helvetica-Bold')

    elements = []

    # Helpers
    def _v(key):
        return _s(d.get(key))

    def _cell(label, value='', min_height=None):
        """Cria conteúdo de célula com label pequeno e valor abaixo."""
        parts = [Paragraph(f"<font size=7 color='#555555'>{label}</font>", cell_label)]
        if value:
            parts.append(Paragraph(str(value), cell_value))
        return parts

    def _cell_p(label, value=''):
        """Retorna lista de Paragraphs para uma célula."""
        content = f"<font size=7 color='#555555'>{label}</font><br/><b>{_s(value)}</b>"
        return Paragraph(content, cell_label)

    # Formatar data de nascimento
    data_nasc_raw = _v('data_nascimento')
    data_nasc_fmt = data_nasc_raw
    if data_nasc_raw and '-' in data_nasc_raw:
        try:
            parts = data_nasc_raw.split('-')
            data_nasc_fmt = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass

    # Formatar estado civil
    ec_map = {'solteiro': 'Solteiro(a)', 'casado': 'Casado(a)', 'divorciado': 'Divorciado(a)',
              'amasiado': 'Amasiado(a)', 'viuvo': 'Viúvo(a)'}
    estado_civil_txt = ec_map.get(_v('estado_civil'), _v('estado_civil'))

    # Sexo
    sexo = _v('sexo')

    # Pai/Mãe status
    pai_status = _v('pai_status')
    mae_status = _v('mae_status')
    pai_vivo_txt = '(X) Vivo' if pai_status == 'vivo' else '( ) Vivo'
    pai_falecido_txt = '(X) Falecido' if pai_status == 'falecido' else '( ) Falecido'
    mae_viva_txt = '(X) Viva' if mae_status == 'viva' else '( ) Viva'
    mae_falecida_txt = '(X) Falecida' if mae_status == 'falecida' else '( ) Falecida'

    # Endereço do aldeeiro completo
    endereco_aldeeiro = _v('endereco')
    if _v('endereco_num'):
        endereco_aldeeiro += f", {_v('endereco_num')}"
    if _v('endereco_apto'):
        endereco_aldeeiro += f" Apto {_v('endereco_apto')}"

    # Ponto de referência
    ponto_ref = _v('ponto_referencia')

    # Cidade/UF
    cidade_uf = _v('cidade')
    if _v('estado'):
        cidade_uf += f"/{_v('estado')}"

    # Com quem mora
    vivo_com = _v('vivo_com')
    mora_pais = _v('mora_com_pais')
    com_quem_mora = ''
    if mora_pais == 'sim':
        vc_map = {'mae': 'Mãe', 'pai': 'Pai', 'ambos': 'Pai e Mãe'}
        com_quem_mora = vc_map.get(vivo_com, '')
    estado_civil_val = _v('estado_civil')
    if estado_civil_val in ('casado', 'amasiado'):
        nome_esposo = _v('nome_esposo')
        if nome_esposo:
            com_quem_mora = f"Cônjuge ({nome_esposo})" if not com_quem_mora else f"{com_quem_mora}, Cônjuge"

    # Telefones do aldeeiro
    tel_res = _v('tel_residencial')
    cel_whats = _v('celular_whatsapp')

    # Religião
    religiao_aldeeiro = _v('religiao')
    religiao_pai = _v('religiao_pai')
    religiao_mae = _v('religiao_mae')
    # Religião da família: combinar pai e mãe
    religiao_familia = ''
    if religiao_pai and religiao_mae:
        if religiao_pai == religiao_mae:
            religiao_familia = religiao_pai
        else:
            religiao_familia = f"Pai: {religiao_pai} / Mãe: {religiao_mae}"
    elif religiao_pai:
        religiao_familia = religiao_pai
    elif religiao_mae:
        religiao_familia = religiao_mae

    # Endereço do pai
    vivem_juntos = _v('vivem_juntos')
    pai_disponivel = pai_status not in ('falecido', 'sem_relacionamento')
    mae_disponivel = mae_status not in ('falecida', 'sem_relacionamento')

    if vivem_juntos == 'sim' and (vivo_com == 'ambos' or (pai_disponivel and mae_disponivel)):
        end_pai = _v('endereco_pais')
        if _v('endereco_pais_num'):
            end_pai += f", {_v('endereco_pais_num')}"
        end_pai_bairro = _v('bairro_pais')
        end_pai_cidade = _v('cidade_pais')
        end_mae = end_pai
        end_mae_bairro = end_pai_bairro
        end_mae_cidade = end_pai_cidade
    else:
        end_pai = _v('endereco_pai')
        if _v('endereco_pai_num'):
            end_pai += f", {_v('endereco_pai_num')}"
        end_pai_bairro = _v('bairro_pai')
        end_pai_cidade = _v('cidade_pai')
        end_mae = _v('endereco_mae')
        if _v('endereco_mae_num'):
            end_mae += f", {_v('endereco_mae_num')}"
        end_mae_bairro = _v('bairro_mae')
        end_mae_cidade = _v('cidade_mae')

    # Endereço completo do pai e mãe
    end_pai_completo = end_pai
    if end_pai_bairro:
        end_pai_completo += f" - {end_pai_bairro}"
    if end_pai_cidade:
        end_pai_completo += f", {end_pai_cidade}"

    end_mae_completo = end_mae
    if end_mae_bairro:
        end_mae_completo += f" - {end_mae_bairro}"
    if end_mae_cidade:
        end_mae_completo += f", {end_mae_cidade}"

    # Verificar se endereço do pai é diferente do aldeeiro
    end_aldeeiro_check = endereco_aldeeiro.lower().strip()
    end_pai_diff = end_pai_completo if end_pai_completo.lower().strip() != end_aldeeiro_check else ''
    # Endereço da mãe diferente do pai
    end_mae_diff = end_mae_completo if end_mae_completo.lower().strip() != end_pai_completo.lower().strip() else ''

    # Nome cônjuge e telefone
    nome_conjuge = _v('nome_esposo') if estado_civil_val in ('casado', 'amasiado') else ''

    # Pessoa com melhor relacionamento
    melhor_relaciona = _v('melhor_relaciona')

    # Parente fazendo a mesma aldeia
    participante = _v('participante_aldeia')
    participante_detalhe = _v('participante_detalhe')
    familia_aldeia = _v('familia_fez_aldeia')
    familia_aldeia_quem = _v('familia_aldeia_quem')
    parente_aldeia_txt = ''
    if participante == 'sim' and participante_detalhe:
        parente_aldeia_txt = participante_detalhe
    if familia_aldeia == 'sim' and familia_aldeia_quem:
        if parente_aldeia_txt:
            parente_aldeia_txt += f'; Já fez aldeia: {familia_aldeia_quem}'
        else:
            parente_aldeia_txt = f'Já fez aldeia: {familia_aldeia_quem}'

    # Filhos
    nome_idade_filhos = _v('nome_idade_filhos')

    # Data entrevista formatada
    data_entrevista_raw = _v('data_entrevista')
    data_entrevista_fmt = data_entrevista_raw
    if data_entrevista_raw and '-' in data_entrevista_raw:
        try:
            parts = data_entrevista_raw.split('-')
            data_entrevista_fmt = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            pass

    nome_entrevistador = _v('nome_entrevistador')
    telefone_entrevistador = _v('telefone_entrevistador')

    # ========== Largura disponível ==========
    page_w = A4[0] - 30 * mm  # total usable width
    LINE_COLOR = HexColor('#000000')

    # ========== CABEÇALHO com logo e "Nº da Cabana" ==========
    # Logo path
    logo_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'img', 'iconeAldeias.jpeg')
    logo_cell = ''
    if os.path.exists(logo_path):
        try:
            logo_cell = RLImage(logo_path, width=28 * mm, height=28 * mm)
        except Exception:
            logo_cell = ''

    cabana_content = Paragraph("Nº da<br/>Cabana:", cabana_style)

    header_data = [[
        logo_cell,
        Paragraph("<b>ALDEIAS DE VIDA</b>", title_style),
        cabana_content
    ]]
    header_table = Table(header_data, colWidths=[32 * mm, page_w - 32 * mm - 30 * mm, 30 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
        ('BOX', (2, 0), (2, 0), 0.5, LINE_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3 * mm))

    # Subtítulo
    elements.append(Paragraph(
        "<b>RELATÓRIO DA ENTREVISTA PARA A COORDENAÇÃO DA VISITAÇÃO</b>", subtitle_style))
    elements.append(Spacer(1, 2 * mm))

    # Instrução
    elements.append(Paragraph(
        "Prezado Entrevistador: Coloque nessa ficha o máximo de informações sobre as pessoas mais "
        "importantes na vida do aldeeiro e como elas podem ser encontradas.", intro_style))
    elements.append(Spacer(1, 3 * mm))

    # ========== TABELA PRINCIPAL ==========
    # Definição das linhas da tabela
    # Usamos 4 colunas base para flexibilidade

    nome_completo = _v('nome_completo')
    idade = _v('idade')
    nficha = ''  # Nº Ficha - deixar vazio para preenchimento manual

    table_style_common = TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, LINE_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ])

    # Linha 1: Nome | Sexo | Idade | Nº Ficha
    row1 = [
        _cell_p('Nome:', nome_completo),
        _cell_p('Sexo:', sexo),
        _cell_p('Idade:', idade),
        _cell_p('Nº Ficha', nficha),
    ]
    t1 = Table([row1], colWidths=[page_w * 0.50, page_w * 0.15, page_w * 0.15, page_w * 0.20])
    t1.setStyle(table_style_common)
    elements.append(t1)

    # Linha 2: Endereço | Bairro
    row2 = [
        _cell_p('Endereço:', endereco_aldeeiro),
        _cell_p('Bairro:', _v('bairro')),
    ]
    t2 = Table([row2], colWidths=[page_w * 0.65, page_w * 0.35])
    t2.setStyle(table_style_common)
    elements.append(t2)

    # Linha 3: Ponto de Referência / Como chegar
    row3 = [_cell_p('Ponto de Referência / Como chegar:', ponto_ref)]
    t3 = Table([row3], colWidths=[page_w])
    t3.setStyle(table_style_common)
    elements.append(t3)

    # Linha 4: Cidade/UF | Estado Civil | Religião do Aldeeiro
    row4 = [
        _cell_p('Cidade/UF:', cidade_uf),
        _cell_p('Estado Civil:', estado_civil_txt),
        _cell_p('Religião do Aldeeiro:', religiao_aldeeiro),
    ]
    t4 = Table([row4], colWidths=[page_w * 0.33, page_w * 0.33, page_w * 0.34])
    t4.setStyle(table_style_common)
    elements.append(t4)

    # Linha 5: Religião da família | Fones do Aldeeiro com operadora (x2) | Com quem o Aldeeiro mora
    row5 = [
        _cell_p('Religião da família:', religiao_familia),
        _cell_p('Fones do Aldeeiro com operadora:', tel_res),
        _cell_p('Fones do Aldeeiro com operadora:', cel_whats),
        _cell_p('Com quem o Aldeeiro mora:', com_quem_mora),
    ]
    t5 = Table([row5], colWidths=[page_w * 0.25, page_w * 0.25, page_w * 0.25, page_w * 0.25])
    t5.setStyle(table_style_common)
    elements.append(t5)

    elements.append(Spacer(1, 2 * mm))

    # Linha 6: Nome do Pai | (Vivo/Falecido) | Telefone com operadora
    nome_pai = _v('nome_pai') if pai_status not in ('sem_relacionamento',) else 'Sem relacionamento'
    tel_pai = _v('telefone_pai')
    row6 = [
        _cell_p('Nome do Pai:', nome_pai),
        Paragraph(f"<font size=8>{pai_vivo_txt}    {pai_falecido_txt}</font>", cell_label),
        _cell_p('Telefone com operadora:', tel_pai),
    ]
    t6 = Table([row6], colWidths=[page_w * 0.40, page_w * 0.30, page_w * 0.30])
    t6.setStyle(table_style_common)
    elements.append(t6)

    # Linha 7: Nome da Mãe | (Viva/Falecida) | Telefone com operadora
    nome_mae = _v('nome_mae') if mae_status not in ('sem_relacionamento',) else 'Sem relacionamento'
    tel_mae = _v('telefone_mae')
    row7 = [
        _cell_p('Nome da Mãe:', nome_mae),
        Paragraph(f"<font size=8>{mae_viva_txt}    {mae_falecida_txt}</font>", cell_label),
        _cell_p('Telefone com operadora:', tel_mae),
    ]
    t7 = Table([row7], colWidths=[page_w * 0.40, page_w * 0.30, page_w * 0.30])
    t7.setStyle(table_style_common)
    elements.append(t7)

    elements.append(Spacer(1, 2 * mm))

    # Linha 8: Endereço do Pai (se diferente) | Endereço da Mãe (se diferente do pai)
    row8 = [
        _cell_p('Endereço do Pai (se for diferente do endereço do Aldeeiro):', end_pai_diff),
        _cell_p('Endereço da mãe (se for diferente do endereço do pai):', end_mae_diff),
    ]
    t8 = Table([row8], colWidths=[page_w * 0.50, page_w * 0.50])
    t8.setStyle(table_style_common)
    elements.append(t8)

    elements.append(Spacer(1, 2 * mm))

    # Linha 9: Nome do Cônjuge | Telefones com operadora (x2)
    row9 = [
        _cell_p('Nome do Cônjuge (se tiver):', nome_conjuge),
        _cell_p('Telefones com operadora:', ''),
        _cell_p('Telefones com Operadora:', ''),
    ]
    t9 = Table([row9], colWidths=[page_w * 0.40, page_w * 0.30, page_w * 0.30])
    t9.setStyle(table_style_common)
    elements.append(t9)

    elements.append(Spacer(1, 2 * mm))

    # Linha 10: Contato amigos/irmãos - VAZIO para preenchimento manual
    row10 = [
        _cell_p('Nome de algum outro contato (amigos, irmãos, etc...)', ''),
        _cell_p('Relacionamento', ''),
        _cell_p('Telefones com Operadora', ''),
    ]
    t10 = Table([row10], colWidths=[page_w * 0.45, page_w * 0.25, page_w * 0.30],
                rowHeights=[22 * mm])
    t10.setStyle(table_style_common)
    elements.append(t10)

    elements.append(Spacer(1, 2 * mm))

    # Linha 11: Nome e idade dos filhos
    row11 = [_cell_p('Nome e idade dos filhos (se tiver):', nome_idade_filhos)]
    t11 = Table([row11], colWidths=[page_w])
    t11.setStyle(table_style_common)
    elements.append(t11)

    elements.append(Spacer(1, 2 * mm))

    # Linha 12: Pessoa(s) com melhor relacionamento | Grau de parentesco
    row12 = [
        _cell_p('Pessoa(s) com melhor relacionamento:', melhor_relaciona),
        _cell_p('Grau de parentesco:', ''),
    ]
    t12 = Table([row12], colWidths=[page_w * 0.55, page_w * 0.45])
    t12.setStyle(table_style_common)
    elements.append(t12)

    elements.append(Spacer(1, 2 * mm))

    # Linha 13: Parente próximo fazendo a mesma aldeia
    row13 = [_cell_p(
        'Tem algum parente próximo fazendo a mesma Aldeia? Ou trabalhando nessa Aldeia? Quem?',
        parente_aldeia_txt
    )]
    t13 = Table([row13], colWidths=[page_w])
    t13.setStyle(table_style_common)
    elements.append(t13)

    elements.append(Spacer(1, 4 * mm))

    # Linha 14: Entrevistador | Data | Fone do Entrevistador
    row14 = [
        _cell_p('Entrevistador (nome legível e assinatura):', nome_entrevistador),
        _cell_p('Data:', data_entrevista_fmt),
        _cell_p('Fone do Entrevistador:', telefone_entrevistador),
    ]
    t14 = Table([row14], colWidths=[page_w * 0.45, page_w * 0.25, page_w * 0.30])
    t14.setStyle(table_style_common)
    elements.append(t14)

    doc.build(elements)
    buffer.seek(0)
    return buffer
