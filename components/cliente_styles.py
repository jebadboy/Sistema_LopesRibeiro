"""
Componente de estilos CSS para o módulo de clientes
Inclui timeline moderna, cards de resumo e otimizações mobile
"""

def get_cliente_css():
    """Retorna CSS customizado para o módulo de clientes"""
    return """
    <style>
    /* ===== TIMELINE MODERNA ===== */
    .cliente-timeline {
        padding: 1rem 0;
        max-height: 500px;
        overflow-y: auto;
        margin: 1rem 0;
    }
    
    .timeline-event {
        position: relative;
        padding-left: 2.5rem;
        padding-bottom: 1.5rem;
        border-left: 3px solid #e3e8ef;
        transition: all 0.3s ease;
    }
    
    .timeline-event:last-child {
        border-left-color: transparent;
        padding-bottom: 0;
    }
    
    .timeline-event:hover {
        border-left-color: #4CAF50;
    }
    
    .timeline-dot {
        position: absolute;
        left: -0.65rem;
        top: 0.2rem;
        width: 1.2rem;
        height: 1.2rem;
        background: #4CAF50;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 0 0 3px #4CAF50;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.7rem;
        color: white;
        font-weight: bold;
    }
    
    .timeline-dot.status { background: #2196F3; box-shadow: 0 0 0 3px #2196F3; }
    .timeline-dot.processo { background: #FF9800; box-shadow: 0 0 0 3px #FF9800; }
    .timeline-dot.financeiro { background: #4CAF50; box-shadow: 0 0 0 3px #4CAF50; }
    .timeline-dot.proposta { background: #9C27B0; box-shadow: 0 0 0 3px #9C27B0; }
    .timeline-dot.documento { background: #607D8B; box-shadow: 0 0 0 3px #607D8B; }
    
    .timeline-date {
        font-size: 0.75rem;
        color: #64748b;
        margin-bottom: 0.3rem;
        font-weight: 500;
    }
    
    .timeline-title {
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 0.2rem;
        font-size: 0.95rem;
    }
    
    .timeline-desc {
        font-size: 0.85rem;
        color: #64748b;
        line-height: 1.5;
    }
    
    /* ===== TEMAS DE CORES ===== */
    .cliente-card.roxo { /* Default */
        background: linear-gradient(120deg, #8E2DE2 0%, #4A00E0 100%);
        color: white;
    }

    .cliente-card.azul {
        background: #06b6d4; /* Azul Piscina (Cyan 500) */
        color: white;
        background-image: linear-gradient(135deg, #06b6d4 0%, #22d3ee 100%);
    }

    .cliente-card.verde {
        background: #86efac; /* Verde Claro (Green 300) */
        color: #14532d;   /* Verde Escuro Text */
        text-shadow: none;
    }
    .cliente-card.verde h2 { color: #14532d; text-shadow: none; }
    .cliente-card.verde p { opacity: 0.9; color: #166534; }
    .cliente-card.verde .metric-item { 
        background: rgba(255,255,255,0.4); 
        color: #14532d; 
        border-color: rgba(20, 83, 45, 0.1); 
    }
    .cliente-card.verde hr { border-top-color: rgba(20, 83, 45, 0.15); }

    .cliente-card.amarelo {
        background: #fde047; /* Amarelo Claro (Yellow 300) */
        color: #422006;   /* Marrom Text */
        text-shadow: none;
    }
    .cliente-card.amarelo h2 { color: #422006; text-shadow: none; }
    .cliente-card.amarelo p { opacity: 0.9; color: #713f12; }
    .cliente-card.amarelo .metric-item { 
        background: rgba(255,255,255,0.4); 
        color: #422006; 
        border-color: rgba(66, 32, 6, 0.1); 
    }
    .cliente-card.amarelo hr { border-top-color: rgba(66, 32, 6, 0.15); }

    .cliente-card.vermelho {
        background: #fca5a5; /* Vermelho Claro (Red 300) */
        color: #7f1d1d;   /* Vermelho Escuro Text */
        text-shadow: none;
    }
    .cliente-card.vermelho h2 { color: #7f1d1d; text-shadow: none; }
    .cliente-card.vermelho p { opacity: 0.9; color: #991b1b; }
    .cliente-card.vermelho .metric-item { 
        background: rgba(255,255,255,0.4); 
        color: #7f1d1d; 
        border-color: rgba(127, 29, 29, 0.1); 
    }
    .cliente-card.vermelho hr { border-top-color: rgba(127, 29, 29, 0.15); }

    /* ===== CARD DE RESUMO DO CLIENTE (DESIGN PREMIUM - AZUL PISCINA FIXO) ===== */
    .cliente-card {
        background: linear-gradient(135deg, #06b6d4 0%, #22d3ee 100%);
        padding: 20px 24px;
        border-radius: 15px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1), 0 10px 20px rgba(6, 182, 212, 0.15);
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
        border: none;
    }
    
    .cliente-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.12), 0 15px 25px rgba(6, 182, 212, 0.2);
    }
    
    .cliente-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: linear-gradient(45deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 100%);
        pointer-events: none;
    }
    
    .cliente-card h2 {
        margin: 0 0 0.5rem 0;
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: #0f172a !important;
        text-shadow: none;
    }
    
    .cliente-card p {
        margin: 0.3rem 0;
        font-size: 1rem;
        font-weight: 400;
        color: #334155 !important;
        opacity: 1;
    }
    
    .cliente-card a {
        color: #0f172a !important;
        font-weight: 500;
    }
    
    .cliente-card hr {
        border: none;
        border-top: 1px solid rgba(15, 23, 42, 0.15);
        margin: 1rem 0;
    }
    
    .cliente-metrics {
        display: flex;
        gap: 0.8rem;
        flex-wrap: wrap;
        margin-top: 0.75rem;
    }
    
    .metric-item {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        background: rgba(255, 255, 255, 0.35);
        padding: 0.5rem 0.8rem;
        border-radius: 10px;
        backdrop-filter: blur(5px);
        font-size: 0.85rem;
        font-weight: 500;
        border: 1px solid rgba(255,255,255,0.4);
        color: #0f172a;
    }
    
    .metric-item b {
        font-weight: 700;
    }

    /* Classe azul mantida para compatibilidade (agora é o padrão) */
    .cliente-card.azul {
        background: linear-gradient(135deg, #06b6d4 0%, #22d3ee 100%);
    }

    /* ===== CARD DE LINKS ATIVOS (COMPACTO) ===== */
    .link-active-container {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); /* Smaller Cards */
        gap: 0.8rem;
        margin-top: 0.8rem;
    }

    .link-active-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.8rem;
        transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .link-active-card:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-color: #cbd5e1;
    }

    /* ===== COMPACTAÇÃO E ESPAÇAMENTO ===== */
    .compact-section {
        margin: 0.3rem 0;
    }
    
    .section-divider {
        border-top: 1px solid #e3e8ef;
        margin: 1rem 0;
    }
    
    /* ===== MOBILE OPTIMIZATIONS ===== */
    @media (max-width: 768px) {
        .cliente-timeline {
            padding-left: 0.2rem;
            max-height: 350px;
        }
        
        .timeline-event {
            padding-left: 1.5rem;
            padding-bottom: 1rem;
        }
        
        .cliente-card {
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        .cliente-card h2 {
            font-size: 1.1rem;
        }
        
        .cliente-metrics {
            gap: 0.5rem;
        }
        
        .metric-item {
            width: auto; /* Allow items to flow */
            font-size: 0.7rem;
            flex-grow: 1; /* Stretch to fill space */
            justify-content: center;
        }

        .link-active-container {
            grid-template-columns: 1fr; /* Stack on mobile */
            gap: 0.8rem;
        }
        
        .link-active-card {
             padding: 1rem; /* Slightly larger targets for touch */
        }
    }
    
    /* ===== ANIMAÇÕES ===== */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-5px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .timeline-event { animation: fadeIn 0.3s ease; }
    .link-active-card { animation: fadeIn 0.3s ease; }
    </style>
    """
