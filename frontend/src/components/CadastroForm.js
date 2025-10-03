import React, { useState } from 'react';
import axios from 'axios';

const CadastroForm = ({ onAccessGranted }) => {
  const [formData, setFormData] = useState({
    nome: '',
    sobrenome: '',
    email: '',
    telefone: '',
    profissao: '',
    senha: ''
  });
  
  const [isLogin, setIsLogin] = useState(false); // Alternar entre cadastro e login
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const API = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  const formatTelefone = (value) => {
    const numbers = value.replace(/\D/g, '');
    if (numbers.length <= 10) {
      return numbers.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
    }
    return numbers.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    
    if (name === 'telefone') {
      setFormData(prev => ({
        ...prev,
        [name]: formatTelefone(value)
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  const validateForm = () => {
    const requiredFields = isLogin 
      ? ['email', 'senha']
      : ['nome', 'sobrenome', 'email', 'telefone', 'profissao', 'senha'];
      
    for (const field of requiredFields) {
      if (!formData[field]?.trim()) {
        setError(`Por favor, preencha o campo ${field}`);
        return false;
      }
    }

    // Validar email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      setError('Por favor, insira um email válido');
      return false;
    }

    // Validar telefone (apenas no cadastro)
    if (!isLogin) {
      const numbers = formData.telefone.replace(/\D/g, '');
      if (numbers.length < 10 || numbers.length > 11) {
        setError('Por favor, insira um telefone válido');
        return false;
      }
    }

    // Validar senha
    if (formData.senha.length < 6) {
      setError('A senha deve ter pelo menos 6 caracteres');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setLoading(true);
    setError('');

    try {
      const endpoint = isLogin ? '/api/login' : '/api/criar-lead';
      const response = await axios.post(`${API}${endpoint}`, formData);
      
      if (response.data.success) {
        const token = response.data.access_token;
        
        // Armazenar dados localmente
        localStorage.setItem('access_token', token);
        localStorage.setItem('lead_data', JSON.stringify({
          email: formData.email,
          nome: formData.nome || response.data.nome,
          login_time: new Date().toISOString()
        }));
        
        // Conceder acesso
        onAccessGranted(token);
      }
    } catch (error) {
      console.error('Erro:', error);
      if (error.response?.status === 401) {
        setError('Email ou senha incorretos');
      } else if (error.response?.status === 409) {
        setError('Este email já está cadastrado. Clique em "Login" acima ou use outro email.');
      } else {
        setError(error.response?.data?.detail || 'Erro ao processar solicitação');
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setError('');
    setFormData({
      nome: '',
      sobrenome: '',
      email: formData.email, // Manter email preenchido
      telefone: '',
      profissao: '',
      senha: ''
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-dark via-primary to-secondary flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-primary-dark mb-2">
            {isLogin ? 'Faça seu Login' : 'Cadastre-se'}
          </h1>
          <p className="text-gray-600">
            {isLogin 
              ? 'Acesse sua conta para usar o simulador' 
              : 'Crie sua conta para acessar o simulador de consórcio'
            }
          </p>
        </div>

        {/* Toggle buttons */}
        <div className="flex bg-gray-100 rounded-lg p-1 mb-6">
          <button
            type="button"
            onClick={() => !isLogin && toggleMode()}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
              !isLogin
                ? 'bg-white text-primary-dark shadow-sm'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Cadastro
          </button>
          <button
            type="button"
            onClick={() => isLogin && toggleMode()}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
              isLogin
                ? 'bg-white text-primary-dark shadow-sm'
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Login
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Campos de cadastro */}
          {!isLogin && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nome *
                  </label>
                  <input
                    type="text"
                    name="nome"
                    value={formData.nome}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                    placeholder="Seu nome"
                    required={!isLogin}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Sobrenome *
                  </label>
                  <input
                    type="text"
                    name="sobrenome"
                    value={formData.sobrenome}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                    placeholder="Seu sobrenome"
                    required={!isLogin}
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Telefone *
                </label>
                <input
                  type="tel"
                  name="telefone"
                  value={formData.telefone}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="(11) 99999-9999"
                  required={!isLogin}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Profissão *
                </label>
                <input
                  type="text"
                  name="profissao"
                  value={formData.profissao}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="Sua profissão"
                  required={!isLogin}
                />
              </div>
            </>
          )}

          {/* Campos comuns (email e senha) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email *
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="seu@email.com"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Senha * {!isLogin && <span className="text-gray-500">(min. 6 caracteres)</span>}
            </label>
            <input
              type="password"
              name="senha"
              value={formData.senha}
              onChange={handleInputChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="••••••••"
              required
            />
          </div>

          {/* Error message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-primary to-secondary text-white py-3 px-4 rounded-lg font-semibold hover:shadow-lg transition-all duration-300 disabled:opacity-50"
          >
            {loading 
              ? (isLogin ? 'Fazendo login...' : 'Criando conta...') 
              : (isLogin ? 'Fazer Login' : 'Criar Conta')
            }
          </button>
        </form>

        {/* Switch mode */}
        <div className="mt-6 text-center">
          <p className="text-gray-600">
            {isLogin ? 'Não tem conta? ' : 'Já tem uma conta? '}
            <button
              type="button"
              onClick={toggleMode}
              className="text-primary font-medium hover:underline"
            >
              {isLogin ? 'Cadastre-se' : 'Faça login'}
            </button>
          </p>
        </div>

        {/* Demo access */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <button
            type="button"
            onClick={() => {
              const demoToken = `demo-${Date.now()}`;
              localStorage.setItem('access_token', demoToken);
              onAccessGranted(demoToken);
            }}
            className="w-full bg-gray-100 text-gray-700 py-2 px-4 rounded-lg font-medium hover:bg-gray-200 transition-all"
          >
            Pular cadastro e ver simulação
          </button>
          <p className="text-xs text-gray-500 mt-2 text-center">
            Acesso temporário - dados não serão salvos
          </p>
        </div>
      </div>
    </div>
  );
};

export default CadastroForm;