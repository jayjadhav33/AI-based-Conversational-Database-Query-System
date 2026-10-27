import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Database, 
  Sparkles, 
  Server, 
  Key, 
  Terminal, 
  Table as TableIcon, 
  Trash2, 
  Plus, 
  Search, 
  LogOut, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Code2, 
  Copy, 
  Check, 
  History, 
  Play, 
  Cpu, 
  ShieldCheck, 
  Layers, 
  MessageSquare,
  X,
  ChevronRight,
  Clock,
  ArrowUpRight
} from 'lucide-react';
import './Dashboard.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const Dashboard = () => {
  const [databases, setDatabases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Modals state
  const [showAddDb, setShowAddDb] = useState(false);
  const [newDb, setNewDb] = useState({ 
    name: '', 
    db_type: 'MySQL', 
    host: 'localhost', 
    port: 3306, 
    database_name: '', 
    username: 'root', 
    password: '' 
  });
  const [testStatus, setTestStatus] = useState(null);
  const [testMsg, setTestMsg] = useState('');
  const [addLoading, setAddLoading] = useState(false);

  const [showSchema, setShowSchema] = useState(false);
  const [selectedTableTab, setSelectedTableTab] = useState(0);
  const [schemaSearch, setSchemaSearch] = useState('');

  const [showQuery, setShowQuery] = useState(false);
  const [queryInput, setQueryInput] = useState('');
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryResults, setQueryResults] = useState(null);

  const [showAskAI, setShowAskAI] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [queryHistory, setQueryHistory] = useState([]);
  const [historySearch, setHistorySearch] = useState('');
  
  // Active data
  const [activeDb, setActiveDb] = useState(null);
  const [schemaData, setSchemaData] = useState(null);
  const [copiedSqlIndex, setCopiedSqlIndex] = useState(null);
  
  // Ask AI State
  const [chatHistory, setChatHistory] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [showSqlFor, setShowSqlFor] = useState({});
  const chatEndRef = useRef(null);

  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchDatabases();
    fetchHistoryCount();
  }, []);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory, aiLoading]);

  const getHeaders = () => ({
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  });

  const fetchDatabases = async () => {
    try {
      const res = await fetch(`${API_URL}/databases/`, { headers: getHeaders() });
      if (res.status === 401) {
        localStorage.removeItem('token');
        navigate('/login');
        return;
      }
      const data = await res.json();
      setDatabases(Array.isArray(data) ? data : []);
    } catch (err) {
      setError("Failed to fetch databases.");
    } finally {
      setLoading(false);
    }
  };

  const fetchHistoryCount = async () => {
    try {
      const res = await fetch(`${API_URL}/ai/history`, { headers: getHeaders() });
      if (res.ok) {
        const data = await res.json();
        setQueryHistory(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const handleTestConnection = async (e) => {
    e.preventDefault();
    setTestStatus('testing');
    setTestMsg('');
    try {
      const res = await fetch(`${API_URL}/databases/test`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ ...newDb, port: parseInt(newDb.port) || 3306 })
      });
      const data = await res.json();
      if (res.ok) {
        setTestStatus('success');
        setTestMsg('Connection verified successfully!');
      } else {
        setTestStatus('error');
        setTestMsg(data.detail || 'Connection failed.');
      }
    } catch {
      setTestStatus('error');
      setTestMsg('Server connection error.');
    }
  };

  const handleAddDatabase = async (e) => {
    e.preventDefault();
    setAddLoading(true);
    try {
      const res = await fetch(`${API_URL}/databases/`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ ...newDb, port: parseInt(newDb.port) || 3306 })
      });
      if (res.ok) {
        setShowAddDb(false);
        setNewDb({ name: '', db_type: 'MySQL', host: 'localhost', port: 3306, database_name: '', username: 'root', password: '' });
        setTestStatus(null);
        fetchDatabases();
      } else {
        const data = await res.json();
        alert(data.detail || "Failed to add database");
      }
    } catch (err) {
      alert("Failed to add database");
    } finally {
      setAddLoading(false);
    }
  };

  const handleDeleteDatabase = async (id, name) => {
    if (!window.confirm(`Are you sure you want to remove connection '${name}'?`)) return;
    try {
      const res = await fetch(`${API_URL}/databases/${id}`, {
        method: 'DELETE',
        headers: getHeaders()
      });
      if (res.ok) {
        if (activeDb?.id === id) {
          setActiveDb(null);
          setShowAskAI(false);
          setShowSchema(false);
          setShowQuery(false);
        }
        await fetchDatabases();
        await fetchHistoryCount();
      } else {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Failed to delete database.");
      }
    } catch (err) {
      alert(`Failed to delete database: ${err.message || 'Unknown network error'}`);
    }
  };

  const handleExtractSchema = async (db) => {
    setActiveDb(db);
    setShowSchema(true);
    setSchemaData(null);
    setSelectedTableTab(0);
    setSchemaSearch('');
    try {
      const res = await fetch(`${API_URL}/schema/${db.id}`, { headers: getHeaders() });
      const data = await res.json();
      if (res.ok) {
        setSchemaData(data);
      } else {
        setError(data.detail);
      }
    } catch (err) {
      setError("Failed to extract schema.");
    }
  };

  const handleOpenPlayground = (db) => {
    setActiveDb(db);
    setQueryInput(`SELECT * FROM customers LIMIT 10;`);
    setQueryResults(null);
    setShowQuery(true);
  };

  const handleRunQuery = async () => {
    if (!queryInput.trim()) return;
    setQueryLoading(true);
    setQueryResults(null);
    try {
      const res = await fetch(`${API_URL}/query/${activeDb.id}`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ sql_query: queryInput })
      });
      const data = await res.json();
      if (res.ok) {
        setQueryResults(data);
      } else {
        alert(data.detail || "Query execution failed");
      }
    } catch (err) {
      alert("Failed to run query.");
    } finally {
      setQueryLoading(false);
    }
  };

  const handleOpenAskAI = (db) => {
    setActiveDb(db);
    setChatHistory([
      { 
        role: 'assistant', 
        content: `👋 Hello! I am your AI Text-to-SQL Assistant powered by a fine-tuned **Qwen2.5-1.5B (QLoRA)** model.\n\nAsk me anything in plain English about the **'${db.database_name}'** database!` 
      }
    ]);
    setShowSqlFor({});
    setShowAskAI(true);
  };

  const handleAskAI = async (overrideQuestion = null) => {
    const q = overrideQuestion || currentQuestion;
    if (!q.trim()) return;
    
    const userMsg = { role: 'user', content: q };
    const newHistory = [...chatHistory, userMsg];
    setChatHistory(newHistory);
    setCurrentQuestion('');
    setAiLoading(true);

    try {
      const res = await fetch(`${API_URL}/ai/ask/${activeDb.id}`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ 
          question: userMsg.content, 
          history: newHistory.slice(1, -1) 
        })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        let aiMsg = "";
        let sql = data.generated_sql;
        
        if (data.error) {
          aiMsg = `⚠️ Execution Error: ${data.error}`;
        } else if (data.results && data.results.rows && data.results.rows.length > 0) {
          const rows = data.results.rows;
          const cols = data.results.columns;
          
          if (rows.length === 1 && cols.length === 1) {
            const val = rows[0][cols[0]];
            const qLower = userMsg.content.toLowerCase();
            if (qLower.includes('how many') || qLower.includes('count')) {
              aiMsg = `Found **${val}** matching record(s).`;
            } else if (qLower.includes('is there') || qLower.includes('exist') || qLower.includes('find') || qLower.includes('presence')) {
              aiMsg = (val > 0 || (typeof val === 'string' && val !== '0')) 
                ? `Yes, found **${val}** in the database.` 
                : `No matching records found for "${userMsg.content}".`;
            } else {
              aiMsg = `Result: **${val}**`;
            }
          } else if (rows.length === 1) {
            const nameField = rows[0]['name'] || rows[0]['doctor_name'] || rows[0]['student_name'] || rows[0][cols[0]];
            const qLower = userMsg.content.toLowerCase();
            if (qLower.includes('is there') || qLower.includes('presence') || qLower.includes('find') || qLower.includes('search')) {
              aiMsg = `Yes, found **${nameField}** in the database:`;
            } else {
              aiMsg = `Found 1 matching record:`;
            }
          } else {
            aiMsg = `Found **${rows.length}** matching record(s):`;
          }
        } else {
          aiMsg = `No matching records found in the database for "${userMsg.content}".`;
        }
        
        setChatHistory([...newHistory, { 
          role: 'assistant', 
          content: aiMsg, 
          sql: sql,
          results: data.results 
        }]);
        fetchHistoryCount();
      } else {
        setChatHistory([...newHistory, { role: 'assistant', content: `❌ Error: ${data.detail}` }]);
      }
    } catch (err) {
      setChatHistory([...newHistory, { role: 'assistant', content: "Failed to connect to the AI model engine." }]);
    } finally {
      setAiLoading(false);
    }
  };

  const handleCopySql = (sql, index) => {
    navigator.clipboard.writeText(sql);
    setCopiedSqlIndex(index);
    setTimeout(() => setCopiedSqlIndex(null), 2000);
  };

  const filteredDatabases = databases.filter(db => 
    db.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    db.database_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    db.host.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="dashboard-layout">
      {/* Background ambient orbs */}
      <div className="ambient-bg">
        <div className="ambient-orb-1"></div>
        <div className="ambient-orb-2"></div>
        <div className="ambient-orb-3"></div>
      </div>

      {/* Top Navigation Bar */}
      <header className="dash-navbar">
        <div className="brand-wrapper">
          <div className="brand-logo-icon">
            <Sparkles size={22} />
          </div>
          <div className="brand-text-title">
            GenAI SQL Hub
            <span className="badge-pill badge-indigo">v2.0</span>
          </div>
        </div>

        <div className="nav-actions-group">
          <button 
            className="btn-modern-secondary"
            onClick={() => { fetchHistoryCount(); setShowHistory(true); }}
          >
            <History size={16} />
            <span>History ({queryHistory.length})</span>
          </button>

          <button className="btn-modern-danger" onClick={handleLogout}>
            <LogOut size={16} />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="dash-main-content">
        
        {/* Stats Overview Grid (3 Cards) */}
        <section className="stats-overview-grid">
          <div className="stat-card">
            <div className="stat-icon-wrapper stat-icon-indigo">
              <Database size={26} />
            </div>
            <div className="stat-meta">
              <span className="stat-label">Connected Databases</span>
              <span className="stat-value">{databases.length}</span>
              <span className="stat-subtext">MySQL Dynamic Introspection</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon-wrapper stat-icon-blue">
              <Cpu size={26} />
            </div>
            <div className="stat-meta">
              <span className="stat-label">AI Inference Engine</span>
              <span className="stat-value" style={{ fontSize: '18px', whiteSpace: 'nowrap' }}>Qwen2.5-1.5B (QLoRA)</span>
              <span className="stat-subtext">4-Bit NF4 • Zero Cloud Leak</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon-wrapper stat-icon-purple">
              <Clock size={26} />
            </div>
            <div className="stat-meta">
              <span className="stat-label">Queries Processed</span>
              <span className="stat-value">{queryHistory.length}</span>
              <span className="stat-subtext">Logged in audit history</span>
            </div>
          </div>
        </section>

        {/* Database Management Section Panel */}
        <section className="dash-section-panel">
          <div className="section-header-bar">
            <div className="section-title-group">
              <h2>Your Database Connections</h2>
              <p>Select a database to ask questions in plain English or explore schemas</p>
            </div>

            <div className="header-controls">
              <div className="search-input-box">
                <Search size={16} className="search-icon" />
                <input 
                  type="text" 
                  className="search-field"
                  placeholder="Search databases..." 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>

              <button 
                className="btn-modern-primary"
                onClick={() => { setShowAddDb(true); setTestStatus(null); setTestMsg(''); }}
              >
                <Plus size={18} />
                <span>Add Connection</span>
              </button>
            </div>
          </div>

          {/* Databases Grid */}
          {loading ? (
            <div className="empty-state-box">
              <Loader2 size={36} className="animate-spin-custom text-indigo-600" />
              <p className="text-slate-500 font-medium">Loading database connections...</p>
            </div>
          ) : filteredDatabases.length === 0 ? (
            <div className="empty-state-box">
              <div className="empty-icon-wrap">
                <Database size={36} />
              </div>
              <h3 className="text-lg font-bold text-slate-800 m-0">No databases found</h3>
              <p className="text-sm text-slate-500 max-w-sm m-0">
                {searchQuery ? "No database matched your search query." : "Connect a MySQL database to begin querying with natural language AI."}
              </p>
              {!searchQuery && (
                <button 
                  className="btn-modern-primary mt-2"
                  onClick={() => setShowAddDb(true)}
                >
                  <Plus size={18} />
                  <span>Add Your First Database</span>
                </button>
              )}
            </div>
          ) : (
            <div className="databases-grid">
              {filteredDatabases.map((db) => (
                <div key={db.id} className="db-card">
                  <div>
                    <div className="db-card-header">
                      <div className="db-card-title-group">
                        <div className="db-engine-avatar">
                          <Server size={22} />
                        </div>
                        <div>
                          <div className="db-name">{db.name}</div>
                          <span className="db-host-badge">{db.host}:{db.port}</span>
                        </div>
                      </div>

                      <span className="badge-pill badge-emerald">
                        <span className="pulse-dot"></span>
                        <span>Ready</span>
                      </span>
                    </div>

                    <div className="db-details-grid mt-4">
                      <div className="db-detail-item">
                        <span className="db-detail-label">Database</span>
                        <span className="db-detail-val truncate">{db.database_name}</span>
                      </div>
                      <div className="db-detail-item">
                        <span className="db-detail-label">Username</span>
                        <span className="db-detail-val truncate">{db.username}</span>
                      </div>
                    </div>
                  </div>

                  <div className="db-actions-row">
                    <button 
                      className="db-action-btn-primary"
                      onClick={() => handleOpenAskAI(db)}
                    >
                      <Sparkles size={16} />
                      <span>Ask AI</span>
                    </button>

                    <button 
                      className="db-action-btn-secondary"
                      onClick={() => handleExtractSchema(db)}
                      title="Inspect Schema"
                    >
                      <TableIcon size={15} />
                      <span>Schema</span>
                    </button>

                    <button 
                      className="db-action-btn-secondary"
                      onClick={() => handleOpenPlayground(db)}
                      title="Manual SQL Playground"
                    >
                      <Terminal size={15} />
                      <span>SQL</span>
                    </button>

                    <button 
                      className="db-delete-btn"
                      onClick={() => handleDeleteDatabase(db.id, db.name)}
                      title="Remove connection"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

      </main>

      {/* ====================================================================
          MODAL 1: ASK AI CONVERSATIONAL WORKSPACE
          ==================================================================== */}
      {showAskAI && activeDb && (
        <div className="modal-backdrop-custom" onClick={() => setShowAskAI(false)}>
          <div className="modal-dialog-custom large-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-custom">
              <div className="modal-title-with-badge">
                <div className="brand-logo-icon" style={{ width: 34, height: 34 }}>
                  <Sparkles size={18} />
                </div>
                <div>
                  <h3>AI Query Assistant</h3>
                  <span className="text-xs text-slate-500 font-mono">
                    Target: <b>{activeDb.database_name}</b> ({activeDb.host})
                  </span>
                </div>
              </div>
              <button className="modal-close-icon-btn" onClick={() => setShowAskAI(false)}>
                <X size={20} />
              </button>
            </div>

            <div className="modal-body-custom">
              <div className="chat-workspace">
                
                {/* Suggested prompt chips */}
                <div className="suggested-prompts-bar">
                  <span className="text-xs font-semibold text-slate-400">Suggestions:</span>
                  <button 
                    className="prompt-chip" 
                    onClick={() => handleAskAI("Show the first 5 records from each table")}
                  >
                    🔍 Sample 5 records
                  </button>
                  <button 
                    className="prompt-chip" 
                    onClick={() => handleAskAI("Show total count of rows across all tables")}
                  >
                    📊 Total row counts
                  </button>
                  <button 
                    className="prompt-chip" 
                    onClick={() => handleAskAI("Show top 5 entries ordered by highest value")}
                  >
                    ⚡ Top 5 highest entries
                  </button>
                </div>

                {/* Chat Feed */}
                <div className="chat-message-feed">
                  {chatHistory.map((msg, index) => (
                    <div 
                      key={index} 
                      className={`msg-row ${msg.role === 'user' ? 'user-msg' : 'ai-msg'}`}
                    >
                      <div className={`msg-avatar ${msg.role === 'user' ? 'user-avatar' : 'ai-avatar'}`}>
                        {msg.role === 'user' ? <Terminal size={18} /> : <Sparkles size={18} />}
                      </div>

                      <div className="msg-bubble-content">
                        <div className="msg-text-bubble">
                          <p style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>
                        </div>

                        {/* Generated SQL Accordion Block */}
                        {msg.sql && (
                          <div className="sql-snippet-box">
                            <div className="sql-snippet-header">
                              <span className="sql-badge-title">
                                <Code2 size={14} />
                                Generated SQL
                              </span>
                              <button 
                                className="copy-sql-btn"
                                onClick={() => handleCopySql(msg.sql, index)}
                              >
                                {copiedSqlIndex === index ? (
                                  <>
                                    <Check size={12} className="text-emerald-400" />
                                    <span className="text-emerald-400">Copied!</span>
                                  </>
                                ) : (
                                  <>
                                    <Copy size={12} />
                                    <span>Copy</span>
                                  </>
                                )}
                              </button>
                            </div>
                            <pre className="sql-code-area">{msg.sql}</pre>
                          </div>
                        )}

                        {/* Tabular Result Preview */}
                        {msg.results && msg.results.rows && msg.results.rows.length > 0 && (
                          <div className="chat-results-table-wrap">
                            <table className="chat-results-table">
                              <thead>
                                <tr>
                                  {msg.results.columns.map((col, cIdx) => (
                                    <th key={cIdx}>{col}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {msg.results.rows.map((row, rIdx) => (
                                  <tr key={rIdx}>
                                    {msg.results.columns.map((col, cIdx) => (
                                      <td key={cIdx}>{String(row[col] ?? 'NULL')}</td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}

                      </div>
                    </div>
                  ))}

                  {aiLoading && (
                    <div className="msg-row ai-msg">
                      <div className="msg-avatar ai-avatar">
                        <Sparkles size={18} />
                      </div>
                      <div className="msg-text-bubble flex items-center gap-3">
                        <Loader2 size={16} className="animate-spin-custom text-indigo-600" />
                        <span className="text-slate-600 text-sm">Synthesizing SQL with Qwen2.5-1.5B &amp; executing...</span>
                      </div>
                    </div>
                  )}

                  <div ref={chatEndRef} />
                </div>

                {/* Chat Input Bar */}
                <form 
                  onSubmit={(e) => { e.preventDefault(); handleAskAI(); }}
                  className="chat-input-bar-container"
                >
                  <input 
                    type="text" 
                    className="chat-input-text"
                    placeholder={`Ask anything about '${activeDb.database_name}' (e.g. 'Show top 5 sales in 2024')...`}
                    value={currentQuestion}
                    onChange={(e) => setCurrentQuestion(e.target.value)}
                    disabled={aiLoading}
                  />
                  <button 
                    type="submit" 
                    className="chat-send-btn" 
                    disabled={aiLoading || !currentQuestion.trim()}
                  >
                    {aiLoading ? <Loader2 size={18} className="animate-spin-custom" /> : <Play size={16} />}
                  </button>
                </form>

              </div>
            </div>
          </div>
        </div>
      )}

      {/* ====================================================================
          MODAL 2: SCHEMA EXPLORER
          ==================================================================== */}
      {showSchema && activeDb && (
        <div className="modal-backdrop-custom" onClick={() => setShowSchema(false)}>
          <div className="modal-dialog-custom large-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-custom">
              <div className="modal-title-with-badge">
                <div className="brand-logo-icon" style={{ width: 34, height: 34, background: '#0284c7' }}>
                  <TableIcon size={18} />
                </div>
                <div>
                  <h3>Database Schema Explorer</h3>
                  <span className="text-xs text-slate-500 font-mono">
                    Database: <b>{activeDb.database_name}</b>
                  </span>
                </div>
              </div>
              <button className="modal-close-icon-btn" onClick={() => setShowSchema(false)}>
                <X size={20} />
              </button>
            </div>

            <div className="modal-body-custom">
              {!schemaData ? (
                <div className="empty-state-box">
                  <Loader2 size={32} className="animate-spin-custom text-blue-600" />
                  <p className="text-slate-500 text-sm">Extracting tables, primary keys, and foreign keys...</p>
                </div>
              ) : schemaData.schema.length === 0 ? (
                <div className="empty-state-box">
                  <p className="text-slate-500 text-sm">No tables found in this database.</p>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 20, height: '100%' }}>
                  
                  {/* Table Selector sidebar */}
                  <div style={{ borderRight: '1px solid #e2e8f0', paddingRight: 16, overflowY: 'auto' }}>
                    <div className="search-input-box mb-3" style={{ width: '100%' }}>
                      <input 
                        type="text" 
                        className="search-field" 
                        style={{ width: '100%', fontSize: 12.5 }}
                        placeholder="Filter tables..." 
                        value={schemaSearch}
                        onChange={(e) => setSchemaSearch(e.target.value)}
                      />
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {schemaData.schema
                        .filter(t => t.table_name.toLowerCase().includes(schemaSearch.toLowerCase()))
                        .map((tbl, idx) => (
                          <button
                            key={idx}
                            onClick={() => setSelectedTableTab(idx)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '9px 12px',
                              borderRadius: 10,
                              background: selectedTableTab === idx ? '#eef2ff' : 'transparent',
                              border: selectedTableTab === idx ? '1px solid #c7d2fe' : '1px solid transparent',
                              color: selectedTableTab === idx ? '#4338ca' : '#334155',
                              fontWeight: selectedTableTab === idx ? 700 : 500,
                              fontSize: 13,
                              cursor: 'pointer',
                              textAlign: 'left'
                            }}
                          >
                            <span className="truncate">{tbl.table_name}</span>
                            <span style={{ fontSize: 11, background: '#e2e8f0', padding: '2px 6px', borderRadius: 6, color: '#475569' }}>
                              {tbl.columns.length}
                            </span>
                          </button>
                      ))}
                    </div>
                  </div>

                  {/* Columns Detail View */}
                  {schemaData.schema[selectedTableTab] && (
                    <div style={{ overflowY: 'auto' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                        <h4 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: '#0f172a' }}>
                          Table: <span style={{ color: '#4f46e5' }}>{schemaData.schema[selectedTableTab].table_name}</span>
                        </h4>
                        <span className="badge-pill badge-blue">
                          {schemaData.schema[selectedTableTab].columns.length} Columns
                        </span>
                      </div>

                      <table className="chat-results-table" style={{ border: '1px solid #e2e8f0', borderRadius: 12 }}>
                        <thead>
                          <tr>
                            <th>Column Name</th>
                            <th>Data Type</th>
                            <th>Constraints &amp; Foreign Keys</th>
                          </tr>
                        </thead>
                        <tbody>
                          {schemaData.schema[selectedTableTab].columns.map((col, cIdx) => {
                            const isPk = schemaData.schema[selectedTableTab].primary_keys.includes(col.name);
                            const fk = schemaData.schema[selectedTableTab].foreign_keys.find(f => f.constrained_columns.includes(col.name));

                            return (
                              <tr key={cIdx}>
                                <td style={{ fontWeight: 600, color: '#0f172a', fontFamily: 'var(--font-mono)' }}>
                                  {col.name}
                                </td>
                                <td>
                                  <span style={{ background: '#f1f5f9', color: '#475569', padding: '2px 8px', borderRadius: 6, fontSize: 11.5, fontFamily: 'var(--font-mono)' }}>
                                    {col.type}
                                  </span>
                                </td>
                                <td>
                                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                    {isPk && (
                                      <span className="badge-pill badge-amber" style={{ fontSize: 11 }}>
                                        <Key size={11} /> PK
                                      </span>
                                    )}
                                    {fk && (
                                      <span className="badge-pill badge-indigo" style={{ fontSize: 11 }}>
                                        FK &rarr; {fk.referred_table}.{fk.referred_columns.join(',')}
                                      </span>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}

                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ====================================================================
          MODAL 3: SQL PLAYGROUND
          ==================================================================== */}
      {showQuery && activeDb && (
        <div className="modal-backdrop-custom" onClick={() => setShowQuery(false)}>
          <div className="modal-dialog-custom large-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-custom">
              <div className="modal-title-with-badge">
                <div className="brand-logo-icon" style={{ width: 34, height: 34, background: '#059669' }}>
                  <Terminal size={18} />
                </div>
                <div>
                  <h3>Manual SQL Playground</h3>
                  <span className="text-xs text-slate-500 font-mono">
                    Target: <b>{activeDb.database_name}</b> (Strict Read-Only SELECT)
                  </span>
                </div>
              </div>
              <button className="modal-close-icon-btn" onClick={() => setShowQuery(false)}>
                <X size={20} />
              </button>
            </div>

            <div className="modal-body-custom" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: '#334155' }}>SQL Query Editor</label>
                <textarea
                  style={{
                    width: '100%',
                    height: 140,
                    background: '#0b0f19',
                    color: '#34d399',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 13,
                    padding: 14,
                    borderRadius: 12,
                    border: '1px solid #1e293b',
                    outline: 'none',
                    resize: 'vertical'
                  }}
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                  placeholder="SELECT * FROM table_name LIMIT 10;"
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                <button 
                  className="btn-modern-primary"
                  onClick={handleRunQuery}
                  disabled={queryLoading || !queryInput.trim()}
                >
                  {queryLoading ? (
                    <>
                      <Loader2 size={16} className="animate-spin-custom" />
                      <span>Executing...</span>
                    </>
                  ) : (
                    <>
                      <Play size={16} />
                      <span>Execute Query</span>
                    </>
                  )}
                </button>
              </div>

              {/* Results */}
              {queryResults && (
                <div style={{ marginTop: 8, flex: 1, overflowY: 'auto' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: '#0f172a' }}>Query Results</span>
                    <span className="badge-pill badge-emerald">
                      {queryResults.rows?.length || 0} Rows Returned
                    </span>
                  </div>

                  <div className="chat-results-table-wrap" style={{ maxHeight: 260 }}>
                    <table className="chat-results-table">
                      <thead>
                        <tr>
                          {queryResults.columns?.map((c, idx) => (
                            <th key={idx}>{c}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {queryResults.rows?.map((row, rIdx) => (
                          <tr key={rIdx}>
                            {queryResults.columns.map((c, cIdx) => (
                              <td key={cIdx}>{String(row[c] ?? 'NULL')}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ====================================================================
          MODAL 4: ADD DATABASE CONNECTION
          ==================================================================== */}
      {showAddDb && (
        <div className="modal-backdrop-custom" onClick={() => setShowAddDb(false)}>
          <div className="modal-dialog-custom" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-custom">
              <div className="modal-title-with-badge">
                <div className="brand-logo-icon" style={{ width: 34, height: 34 }}>
                  <Database size={18} />
                </div>
                <h3>Connect MySQL Database</h3>
              </div>
              <button className="modal-close-icon-btn" onClick={() => setShowAddDb(false)}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleAddDatabase} className="modal-body-custom auth-form">
              {testStatus && (
                <div className={`auth-alert-error ${testStatus === 'success' ? 'badge-emerald' : ''}`} style={{ background: testStatus === 'success' ? '#ecfdf5' : '#fff1f2', color: testStatus === 'success' ? '#059669' : '#e11d48' }}>
                  {testStatus === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
                  <span>{testMsg}</span>
                </div>
              )}

              <div className="auth-input-group">
                <label className="auth-input-label">Connection Nickname</label>
                <input 
                  type="text" 
                  className="auth-input-field" 
                  style={{ paddingLeft: 14 }}
                  placeholder="e.g. Production Sales DB"
                  value={newDb.name}
                  onChange={(e) => setNewDb({ ...newDb, name: e.target.value })}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12 }}>
                <div className="auth-input-group">
                  <label className="auth-input-label">Host Address</label>
                  <input 
                    type="text" 
                    className="auth-input-field"
                    style={{ paddingLeft: 14 }}
                    placeholder="localhost or 127.0.0.1"
                    value={newDb.host}
                    onChange={(e) => setNewDb({ ...newDb, host: e.target.value })}
                    required
                  />
                </div>
                <div className="auth-input-group">
                  <label className="auth-input-label">Port</label>
                  <input 
                    type="number" 
                    className="auth-input-field"
                    style={{ paddingLeft: 14 }}
                    value={newDb.port}
                    onChange={(e) => setNewDb({ ...newDb, port: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="auth-input-group">
                <label className="auth-input-label">Database Name</label>
                <input 
                  type="text" 
                  className="auth-input-field"
                  style={{ paddingLeft: 14 }}
                  placeholder="e.g. store_db"
                  value={newDb.database_name}
                  onChange={(e) => setNewDb({ ...newDb, database_name: e.target.value })}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="auth-input-group">
                  <label className="auth-input-label">Username</label>
                  <input 
                    type="text" 
                    className="auth-input-field"
                    style={{ paddingLeft: 14 }}
                    placeholder="root"
                    value={newDb.username}
                    onChange={(e) => setNewDb({ ...newDb, username: e.target.value })}
                    required
                  />
                </div>
                <div className="auth-input-group">
                  <label className="auth-input-label">Password</label>
                  <input 
                    type="password" 
                    className="auth-input-field"
                    style={{ paddingLeft: 14 }}
                    placeholder="••••••••"
                    value={newDb.password}
                    onChange={(e) => setNewDb({ ...newDb, password: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
                <button 
                  type="button" 
                  className="btn-modern-secondary" 
                  style={{ flex: 1 }}
                  onClick={handleTestConnection}
                  disabled={testStatus === 'testing'}
                >
                  {testStatus === 'testing' ? (
                    <>
                      <Loader2 size={16} className="animate-spin-custom" />
                      <span>Pinging DB...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 size={16} />
                      <span>Test Connection</span>
                    </>
                  )}
                </button>

                <button 
                  type="submit" 
                  className="btn-modern-primary"
                  style={{ flex: 1 }}
                  disabled={addLoading}
                >
                  {addLoading ? (
                    <>
                      <Loader2 size={16} className="animate-spin-custom" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <span>Save &amp; Connect</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ====================================================================
          MODAL 5: QUERY HISTORY AUDIT
          ==================================================================== */}
      {showHistory && (
        <div className="modal-backdrop-custom" onClick={() => setShowHistory(false)}>
          <div className="modal-dialog-custom history-modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header-custom">
              <div className="modal-title-with-badge">
                <div className="brand-logo-icon" style={{ width: 34, height: 34 }}>
                  <History size={18} />
                </div>
                <div>
                  <h3>Query History &amp; Audit Log</h3>
                  <span className="text-xs text-slate-500">Historical questions synthesized and executed</span>
                </div>
              </div>
              <button className="modal-close-icon-btn" onClick={() => setShowHistory(false)}>
                <X size={20} />
              </button>
            </div>

            <div className="modal-body-custom history-modal-body">
              <div className="history-search-bar-wrap">
                <div className="search-input-box" style={{ width: '100%' }}>
                  <Search size={16} className="search-icon" />
                  <input 
                    type="text" 
                    className="search-field"
                    style={{ width: '100%' }}
                    placeholder="Filter past queries by question, database, or SQL keyword..."
                    value={historySearch}
                    onChange={(e) => setHistorySearch(e.target.value)}
                  />
                </div>
              </div>

              {queryHistory.length === 0 ? (
                <div className="empty-state-box" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <p className="text-slate-500 text-sm">No query logs recorded yet.</p>
                </div>
              ) : (
                <div className="history-table-viewport">
                  <table className="history-data-table">
                    <thead>
                      <tr>
                        <th style={{ width: '150px' }}>Date &amp; Time</th>
                        <th style={{ width: '180px' }}>Database</th>
                        <th style={{ width: '32%' }}>User Question</th>
                        <th>Synthesized SQL</th>
                      </tr>
                    </thead>
                    <tbody>
                      {queryHistory
                        .filter(h => 
                          (h.question || '').toLowerCase().includes(historySearch.toLowerCase()) ||
                          (h.generated_sql || '').toLowerCase().includes(historySearch.toLowerCase()) ||
                          (h.database_name || '').toLowerCase().includes(historySearch.toLowerCase())
                        )
                        .map((item) => (
                          <tr key={item.id}>
                            <td className="history-cell-datetime">
                              <div className="history-datetime-block">
                                <span className="history-date-text">
                                  {new Date(item.created_at).toLocaleDateString(undefined, {
                                    month: 'short',
                                    day: 'numeric',
                                    year: 'numeric'
                                  })}
                                </span>
                                <span className="history-time-text">
                                  {new Date(item.created_at).toLocaleTimeString(undefined, {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                    hour12: true
                                  })}
                                </span>
                              </div>
                            </td>
                            <td>
                              <span className="badge-pill badge-blue history-db-badge">
                                {item.database_name}
                              </span>
                            </td>
                            <td className="history-cell-question">
                              {item.question}
                            </td>
                            <td className="history-cell-sql">
                              <code className="history-sql-code">
                                {item.generated_sql}
                              </code>
                            </td>
                          </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="history-modal-footer">
                <span>
                  Showing <b>{queryHistory.filter(h => 
                    (h.question || '').toLowerCase().includes(historySearch.toLowerCase()) ||
                    (h.generated_sql || '').toLowerCase().includes(historySearch.toLowerCase()) ||
                    (h.database_name || '').toLowerCase().includes(historySearch.toLowerCase())
                  ).length}</b> of <b>{queryHistory.length}</b> total query executions
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default Dashboard;
