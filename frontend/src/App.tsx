import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { KnowledgeBasesListPage } from './pages/knowledge-bases/KnowledgeBasesListPage';
import { CreateKnowledgeBasePage } from './pages/knowledge-bases/CreateKnowledgeBasePage';
import { KnowledgeBaseDetailPage } from './pages/knowledge-bases/KnowledgeBaseDetailPage';
import { OntologiesListPage } from './pages/ontologies/OntologiesListPage';
import { CreateOntologyPage } from './pages/ontologies/CreateOntologyPage';
import { OntologyDetailPage } from './pages/ontologies/OntologyDetailPage';
import { QueryPlaygroundView } from './pages/playground/QueryPlaygroundView';

export const App: React.FC = () => {
  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-100">
      {/* Persistent Left Sidebar */}
      <Sidebar />

      {/* Right Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header />

        <Routes>
          <Route path="/" element={<Navigate to="/knowledge-bases" replace />} />
          
          {/* Knowledge Bases Routes */}
          <Route path="/knowledge-bases" element={<KnowledgeBasesListPage />} />
          <Route path="/knowledge-bases/new" element={<CreateKnowledgeBasePage />} />
          <Route path="/knowledge-bases/:kbId" element={<KnowledgeBaseDetailPage />} />

          {/* Ontologies Routes */}
          <Route path="/ontologies" element={<OntologiesListPage />} />
          <Route path="/ontologies/new" element={<CreateOntologyPage />} />
          <Route path="/ontologies/:id" element={<OntologyDetailPage />} />

          {/* RAG Playground Route */}
          <Route path="/playground" element={<QueryPlaygroundView />} />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/knowledge-bases" replace />} />
        </Routes>
      </div>
    </div>
  );
};
