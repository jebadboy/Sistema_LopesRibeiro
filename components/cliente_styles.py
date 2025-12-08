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
    
    /* ===== CARD DE RESUMO DO CLIENTE ===== */
    .cliente-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 16px rgba(102, 126, 234, 0.25);
    }
    
    .cliente-card h2 {
        margin: 0 0 0.5rem 0;
        font-size: 1.5rem;
        font-weight: 700;
    }
    
    .cliente-card p {
        margin: 0.3rem 0;
        font-size: 0.95rem;
        opacity: 0.95;
    }
    
    .cliente-card hr {
        border: none;
        border-top: 1px solid rgba(255, 255, 255, 0.3);
        margin: 1rem 0;
    }
    
    .cliente-metrics {
        display: flex;
        gap: 1.5rem;
        flex-wrap: wrap;
        margin-top: 0.5rem;
    }
    
    .metric-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* ===== COMPACTAÇÃO E ESPAÇAMENTO ===== */
    .compact-section {
        margin: 0.5rem 0;
    }
    
    .section-divider {
        border-top: 1px solid #e3e8ef;
        margin: 1.5rem 0;
    }
    
    /* ===== MOBILE OPTIMIZATIONS ===== */
    @media (max-width: 768px) {
        .cliente-timeline {
            padding-left: 0.5rem;
            max-height: 400px;
        }
        
        .timeline-event {
            padding-left: 2rem;
            padding-bottom: 1.2rem;
        }
        
        .timeline-dot {
            left: -0.55rem;
            width: 1rem;
            height: 1rem;
        }
        
        .cliente-card {
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        .cliente-card h2 {
            font-size: 1.25rem;
        }
        
        .cliente-metrics {
            gap: 1rem;
        }
        
        .timeline-title {
            font-size: 0.9rem;
        }
        
        .timeline-desc {
            font-size: 0.8rem;
        }
    }
    
    /* ===== FILTROS DE TIMELINE ===== */
    .timeline-filters {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-bottom: 1rem;
    }
    
    .filter-badge {
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        cursor: pointer;
        transition: all 0.2s;
        border: 1px solid #e3e8ef;
        background: white;
    }
    
    .filter-badge:hover {
        background: #f8fafc;
        border-color: #cbd5e1;
    }
    
    .filter-badge.active {
        background: #4CAF50;
        color: white;
        border-color: #4CAF50;
    }
    
    /* ===== SCROLLBAR CUSTOMIZADA ===== */
    .cliente-timeline::-webkit-scrollbar {
        width: 6px;
    }
    
    .cliente-timeline::-webkit-scrollbar-track {
        background: #f1f5f9;
        border-radius: 10px;
    }
    
    .cliente-timeline::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 10px;
    }
    
    .cliente-timeline::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }
    
    /* ===== ANIMAÇÕES ===== */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .timeline-event {
        animation: fadeIn 0.3s ease;
    }
    </style>
    """
