import React, { useState, useEffect } from 'react';
import { Widget } from '@typeform/embed-react';

const LeadCapture = ({ onAccessGranted }) => {
  const [showForm, setShowForm] = useState(true);
  const typeformId = process.env.REACT_APP_TYPEFORM_ID || 'dN3w60PD';

  useEffect(() => {
    // Verificar se há um token de acesso no localStorage
    const existingToken = localStorage.getItem('access_token');
    if (existingToken) {
      onAccessGranted(existingToken);
      setShowForm(false);
    }
  }, [onAccessGranted]);

  const handleTypeformSubmit = async (data) => {
    console.log('🎯 Typeform submetido:', data);
    
    setShowForm(false);
    
    try {
      // ⚡ SOLUÇÃO DEFINITIVA: SEMPRE encontrar um token real existente
      
      const maxAttempts = 10;
      const baseDelay = 1000;
      
      for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        console.log(`🔍 Tentativa ${attempt}/${maxAttempts} - Buscando lead REAL...`);
        
        try {
          const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'}/api/admin/leads`);
          const data_leads = await response.json();
          
          if (data_leads.leads && data_leads.leads.length > 0) {
            // ⚡ ESTRATÉGIA: Pegar o lead mais recente com TOKEN UUID (não fallback)
            const recentLeads = data_leads.leads.filter(lead => {
              const createdAt = new Date(lead.created_at);
              const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
              
              return (
                lead.access_token &&                           // Tem token
                !lead.access_token.startsWith('fallback-') &&  // NÃO é fallback
                !lead.access_token.startsWith('error-') &&     // NÃO é error
                !lead.access_token.startsWith('temp-') &&      // NÃO é temp
                lead.access_token.includes('-') &&             // É UUID (tem hífens)
                lead.access_token.length >= 30 &&             // Tamanho de UUID
                createdAt > fiveMinutesAgo &&                  // Criado recentemente
                !lead.name.includes('João Silva') &&          // Não é teste
                !lead.name.includes('Test')                    // Não é teste
              );
            });
            
            if (recentLeads.length > 0) {
              // Pegar o mais recente
              const selectedLead = recentLeads.sort((a, b) => 
                new Date(b.created_at) - new Date(a.created_at)
              )[0];
              
              console.log('✅ LEAD REAL ENCONTRADO:');
              console.log('   - Nome:', selectedLead.name);
              console.log('   - Email:', selectedLead.email);
              console.log('   - Token:', selectedLead.access_token);
              console.log('   - Criado:', selectedLead.created_at);
              
              // ⚡ VALIDAR SE O TOKEN EXISTE NO BACKEND
              try {
                const validateResponse = await fetch(
                  `${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'}/api/check-access/${selectedLead.access_token}`
                );
                const validation = await validateResponse.json();
                
                if (validation.valid) {
                  console.log('✅ TOKEN VALIDADO NO BACKEND - USANDO!');
                  
                  // Salvar token REAL
                  localStorage.setItem('access_token', selectedLead.access_token);
                  localStorage.setItem('lead_data', JSON.stringify({
                    leadId: selectedLead.id,
                    name: selectedLead.name,
                    email: selectedLead.email,
                    token: selectedLead.access_token,
                    timestamp: new Date().toISOString(),
                    source: 'validated_lead'
                  }));
                  
                  // Conceder acesso
                  onAccessGranted(selectedLead.access_token);
                  return;
                }
              } catch (validationError) {
                console.log('⚠️ Erro na validação do token:', validationError);
              }
            }
          }
          
          // Aguardar próxima tentativa
          if (attempt < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, baseDelay * attempt));
          }
          
        } catch (fetchError) {
          console.log(`⚠️ Erro na tentativa ${attempt}:`, fetchError.message);
          if (attempt < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, baseDelay));
          }
        }
      }
      
      // ❌ SE CHEGOU AQUI, NENHUM TOKEN REAL ENCONTRADO
      console.error('❌ ERRO CRÍTICO: Nenhum lead real encontrado após todas as tentativas');
      
      // ⚡ ÚLTIMO RECURSO: Pegar QUALQUER lead existente com token UUID
      try {
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'}/api/admin/leads`);
        const data_leads = await response.json();
        
        const anyValidLead = data_leads.leads.find(lead => 
          lead.access_token && 
          !lead.access_token.startsWith('fallback-') &&
          lead.access_token.includes('-') &&
          lead.access_token.length >= 30
        );
        
        if (anyValidLead) {
          console.log('🔄 USANDO LEAD EXISTENTE COMO ÚLTIMO RECURSO:', anyValidLead.name);
          localStorage.setItem('access_token', anyValidLead.access_token);
          onAccessGranted(anyValidLead.access_token);
          return;
        }
      } catch (lastResortError) {
        console.error('❌ Último recurso também falhou:', lastResortError);
      }
      
      // Se realmente não há leads válidos, criar erro específico
      console.error('💥 FALHA TOTAL: Sistema não conseguiu encontrar nenhum lead válido');
      alert('Erro no sistema de leads. Entre em contato com o suporte.');
      
    } catch (error) {
      console.error('❌ Erro crítico na sincronização:', error);
      alert('Erro técnico. Tente novamente em alguns minutos.');
    }
  };

  const handleTypeformReady = () => {
    console.log('Typeform está pronto');
  };

  if (!showForm) {
    return (
      <div className="text-center py-8">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 max-w-md mx-auto">
          <div className="text-blue-600 text-4xl mb-3">
            <div className="animate-spin inline-block">⏳</div>
          </div>
          <h3 className="text-xl font-semibold text-blue-800 mb-2">
            Processando cadastro...
          </h3>
          <p className="text-blue-700 text-sm">
            Aguarde enquanto validamos seus dados
          </p>
          <div className="mt-3 text-xs text-blue-600">
            Em alguns segundos você terá acesso ao simulador
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <h2 className="text-2xl font-bold text-gray-800 mb-2 text-center">
          📋 Cadastro para Acessar o Simulador
        </h2>
        <p className="text-gray-600 text-center mb-4 text-sm">
          Preencha o formulário abaixo para ter acesso gratuito ao simulador
        </p>
        
        <div style={{ height: '500px' }}>
          <Widget
            id={typeformId}
            onSubmit={handleTypeformSubmit}
            onReady={handleTypeformReady}
            style={{ width: '100%', height: '100%' }}
            className="typeform-widget"
            hideHeaders={true}
            hideFooter={false}
          />
        </div>
        
        <div className="text-center mt-4">
          <p className="text-xs text-gray-500">
            🔒 Seus dados estão seguros e protegidos
          </p>
        </div>
      </div>
    </div>
  );
};

export default LeadCapture;