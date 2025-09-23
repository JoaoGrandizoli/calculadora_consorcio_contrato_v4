import React, { useState } from 'react';
import { Widget } from '@typeform/embed-react';

const LeadCapture = ({ onAccessGranted }) => {
  const [showForm, setShowForm] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFormSubmit = async (event) => {
    console.log('Typeform submitted:', event);
    setIsLoading(true);
    
    // Simulando processo de verificação
    // Em produção, você receberá o access_token do webhook
    setTimeout(() => {
      const mockAccessToken = 'demo-access-token-' + Date.now();
      localStorage.setItem('access_token', mockAccessToken);
      onAccessGranted(mockAccessToken);
      setShowForm(false);
      setIsLoading(false);
    }, 2000);
  };

  const handleFormError = (error) => {
    console.error('Typeform error:', error);
    setError('Erro ao carregar o formulário. Tente novamente.');
    setIsLoading(false);
  };

  if (!showForm) {
    return (
      <div className="text-center py-8">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 max-w-md mx-auto">
          <div className="text-green-600 text-2xl mb-2">✅</div>
          <h3 className="text-lg font-semibold text-green-800 mb-2">
            Acesso Liberado!
          </h3>
          <p className="text-green-700">
            Obrigado por fornecer suas informações. Você já pode usar o simulador de consórcio.
          </p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Processando suas informações...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md mx-auto">
          <div className="text-red-600 text-2xl mb-2">❌</div>
          <h3 className="text-lg font-semibold text-red-800 mb-2">
            Erro no Formulário
          </h3>
          <p className="text-red-700 mb-4">{error}</p>
          <button 
            onClick={() => {
              setError(null);
              setShowForm(true);
            }}
            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
          >
            Tentar Novamente
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-4 text-center">
          Acesse o Simulador de Consórcio
        </h2>
        <p className="text-gray-600 text-center mb-6">
          Para liberar o acesso ao simulador, precisamos de algumas informações básicas.
          <br />
          <strong>Campos obrigatórios:</strong> Nome, E-mail e Telefone
          <br />
          <strong>Campos opcionais:</strong> Patrimônio e Renda (nos ajudam a personalizar a experiência)
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div style={{ height: '600px' }}>
          {process.env.REACT_APP_TYPEFORM_ID ? (
            <Widget
              id={process.env.REACT_APP_TYPEFORM_ID}
              style={{ width: '100%', height: '100%' }}
              className="typeform-widget"
              onSubmit={handleFormSubmit}
              onError={handleFormError}
              onReady={() => console.log('Typeform ready')}
            />
          ) : (
            <div className="flex items-center justify-center h-full bg-gray-50">
              <div className="text-center">
                <h3 className="text-lg font-semibold text-gray-800 mb-2">
                  Formulário não configurado
                </h3>
                <p className="text-gray-600 mb-4">
                  Configure a variável REACT_APP_TYPEFORM_ID no arquivo .env
                </p>
                <button 
                  onClick={() => {
                    // Bypass para desenvolvimento - simular acesso liberado
                    const mockAccessToken = 'demo-access-token-' + Date.now();
                    localStorage.setItem('access_token', mockAccessToken);
                    onAccessGranted(mockAccessToken);
                    setShowForm(false);
                  }}
                  className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
                >
                  Pular (Desenvolvimento)
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 text-center text-sm text-gray-500">
        <p>🔒 Seus dados são seguros e não serão compartilhados com terceiros.</p>
      </div>
    </div>
  );
};

export default LeadCapture;