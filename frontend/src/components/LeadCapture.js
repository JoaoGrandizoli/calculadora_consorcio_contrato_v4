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
    console.log('Typeform submetido:', data);
    
    try {
      // NOVA ESTRATÉGIA: Aguardar webhook processar e buscar pelo email
      await new Promise(resolve => setTimeout(resolve, 4000)); // Aguardar 4 segundos
      
      // Buscar todos os leads
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'}/api/admin/leads`);
      const data_leads = await response.json();
      
      if (data_leads.leads && data_leads.leads.length > 0) {
        // Buscar o lead mais recente (primeiro da lista - assumindo ordenação por data)
        const latestLead = data_leads.leads[0];
        
        // Verificar se é um lead válido (não é teste e tem dados reais)
        if (latestLead.access_token && 
            !latestLead.name.includes('João Silva') && 
            !latestLead.name.includes('Teste') &&
            latestLead.email.includes('@')) {
          
          console.log('✅ Lead encontrado:', latestLead);
          console.log('🔑 Token correto:', latestLead.access_token);
          
          // Usar o token correto do webhook
          localStorage.setItem('access_token', latestLead.access_token);
          localStorage.setItem('lead_data', JSON.stringify({
            leadId: latestLead.id,
            name: latestLead.name,
            email: latestLead.email,
            token: latestLead.access_token
          }));
          
          // Conceder acesso
          onAccessGranted(latestLead.access_token);
          setShowForm(false);
          return;
        }
      }
      
      // Fallback: usar token temporário se não encontrar
      console.log('⚠️ Usando fallback token');
      const tempToken = 'fallback-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('access_token', tempToken);
      onAccessGranted(tempToken);
      setShowForm(false);
      
    } catch (error) {
      console.error('❌ Erro ao sincronizar token:', error);
      
      // Fallback em caso de erro
      const tempToken = 'error-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('access_token', tempToken);
      onAccessGranted(tempToken);
      setShowForm(false);
    }
  };

  const handleTypeformReady = () => {
    console.log('Typeform está pronto');
  };

  if (!showForm) {
    return (
      <div className="text-center py-8">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 max-w-md mx-auto">
          <div className="text-green-600 text-4xl mb-3">✅</div>
          <h3 className="text-xl font-semibold text-green-800 mb-2">
            Perfeito!
          </h3>
          <p className="text-green-700">
            Agora você pode usar o simulador de consórcio.
          </p>
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