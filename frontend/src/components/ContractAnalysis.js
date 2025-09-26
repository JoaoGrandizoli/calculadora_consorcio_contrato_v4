import React, { useState } from 'react';
import { Button } from './ui/button';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { FileText, Upload, AlertCircle, CheckCircle, Star, Loader, File } from 'lucide-react';

const ContractAnalysis = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);

  const handleFileSelect = (file) => {
    if (!file) return;
    
    // Verificar se é PDF
    if (file.type !== 'application/pdf') {
      setError('Por favor, selecione apenas arquivos PDF');
      return;
    }
    
    // Verificar tamanho (10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('Arquivo muito grande (limite: 10MB)');
      return;
    }
    
    setSelectedFile(file);
    setError('');
    console.log('📄 Arquivo selecionado:', file.name, `(${(file.size / 1024 / 1024).toFixed(2)} MB)`);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragActive(false);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError('Por favor, selecione um arquivo PDF');
      return;
    }

    setLoading(true);
    setError('');
    setAnalysis(null);

    try {
      const formData = new FormData();
      formData.append('pdf_file', selectedFile);

      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/analisar-contrato`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao analisar contrato');
      }

      const result = await response.json();
      setAnalysis(result);

    } catch (error) {
      console.error('Erro na análise:', error);
      setError(error.message || 'Erro ao analisar contrato. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  const parseAnalysis = (analysisText) => {
    const sections = {};
    const lines = analysisText.split('\n');
    let currentSection = '';
    let currentContent = [];

    lines.forEach(line => {
      const trimmed = line.trim();
      
      // Detectar seções pelos números e asteriscos
      if (trimmed.match(/^\d+\.\s*\*\*.*\*\*/) || trimmed.match(/^\*\*\d+\..*\*\*/)) {
        // Salvar seção anterior se existe
        if (currentSection && currentContent.length > 0) {
          sections[currentSection] = currentContent.join('\n').trim();
        }
        
        // Nova seção
        currentSection = trimmed.replace(/^\d+\.\s*\*\*/, '').replace(/\*\*/g, '').trim();
        currentContent = [];
      } else if (trimmed && currentSection) {
        currentContent.push(trimmed);
      }
    });

    // Salvar última seção
    if (currentSection && currentContent.length > 0) {
      sections[currentSection] = currentContent.join('\n').trim();
    }

    return sections;
  };

  const renderSection = (title, content, icon) => {
    if (!content) return null;
    
    return (
      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            {icon}
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="whitespace-pre-wrap text-sm leading-relaxed">
            {content}
          </div>
        </CardContent>
      </Card>
    );
  };

  const sections = analysis ? parseAnalysis(analysis.analysis) : {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="mx-auto h-16 w-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
          <FileText className="h-8 w-8 text-blue-600" />
        </div>
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          Análise Inteligente de Contratos
        </h2>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Cole o texto do seu contrato de consórcio e nossa IA irá analisar todos os detalhes, 
          identificar pontos importantes e dar recomendações personalizadas.
        </p>
      </div>

      {/* Input do contrato */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Texto do Contrato
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <textarea
              value={contractText}
              onChange={(e) => setContractText(e.target.value)}
              placeholder="Cole aqui o texto completo do seu contrato de consórcio..."
              className="w-full h-64 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              disabled={loading}
            />
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">
                {contractText.length} caracteres (mínimo 100)
              </span>
              
              <Button 
                onClick={handleAnalyze}
                disabled={loading || contractText.length < 100}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {loading ? (
                  <>
                    <Loader className="mr-2 h-4 w-4 animate-spin" />
                    Analisando...
                  </>
                ) : (
                  <>
                    <FileText className="mr-2 h-4 w-4" />
                    Analisar Contrato
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Erro */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-700">
              <AlertCircle className="h-5 w-5" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading */}
      {loading && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center gap-3 text-blue-600 py-8">
              <Loader className="h-6 w-6 animate-spin" />
              <span className="text-lg">Analisando seu contrato com IA...</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Resultados da análise */}
      {analysis && (
        <div className="space-y-6">
          <div className="flex items-center gap-2 text-green-700 mb-4">
            <CheckCircle className="h-6 w-6" />
            <span className="text-lg font-semibold">Análise Concluída</span>
          </div>

          {renderSection(
            'RESUMO EXECUTIVO', 
            sections['RESUMO EXECUTIVO'], 
            <FileText className="h-5 w-5 text-blue-600" />
          )}
          
          {renderSection(
            'ANÁLISE FINANCEIRA', 
            sections['ANÁLISE FINANCEIRA'], 
            <span className="text-green-600">💰</span>
          )}
          
          {renderSection(
            'PONTOS DE ATENÇÃO', 
            sections['PONTOS DE ATENÇÃO'], 
            <AlertCircle className="h-5 w-5 text-yellow-600" />
          )}
          
          {renderSection(
            'RECOMENDAÇÕES', 
            sections['RECOMENDAÇÕES'], 
            <CheckCircle className="h-5 w-5 text-green-600" />
          )}
          
          {renderSection(
            'SCORE DE RECOMENDAÇÃO', 
            sections['SCORE DE RECOMENDAÇÃO'], 
            <Star className="h-5 w-5 text-yellow-500" />
          )}

          {/* Info sobre o modelo */}
          <Card className="bg-gray-50">
            <CardContent className="pt-6">
              <div className="text-xs text-gray-500 text-center">
                <p>Análise realizada por Claude AI • {analysis.model_used}</p>
                <p>Data: {new Date(analysis.timestamp).toLocaleString('pt-BR')}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default ContractAnalysis;