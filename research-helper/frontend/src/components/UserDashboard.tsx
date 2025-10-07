import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from './AuthContext';
import { Mail, Calendar, User, School, ExternalLink, Trash2, Plus } from 'lucide-react';
import { API_BASE } from './config.ts';

interface Connection {
  id: string;
  professorName: string;
  university: string;
  email: string;
  field: string;
  status: 'pending' | 'responded' | 'no_response';
  dateContacted: string;
  notes?: string;
}

//const API_BASE = "https://finalresearchhelper-production.up.railway.app";
//const API_BASE = "http://localhost:5050";

const UserDashboard: React.FC = () => {
  const { user } = useContext(AuthContext);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);
  const [editedStatuses, setEditedStatuses] = useState<{ [id: string]: Connection['status'] }>({});
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    responded: 0,
    noResponse: 0,
  });

  useEffect(() => {
    fetchConnections();
  }, []);

  const fetchConnections = async () => {
    try {
      const token = localStorage.getItem('research_helper_token');
      const response = await fetch(`${API_BASE}/user/connections`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setConnections(data.connections || []);
        calculateStats(data.connections || []);
      }
    } catch (error) {
      console.error('Failed to fetch connections:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (connectionsList: Connection[]) => {
    const stats = {
      total: connectionsList.length,
      pending: connectionsList.filter(c => c.status === 'pending').length,
      responded: connectionsList.filter(c => c.status === 'responded').length,
      noResponse: connectionsList.filter(c => c.status === 'no_response').length,
    };
    setStats(stats);
  };

  const saveAllStatuses = async () => {
    if (Object.keys(editedStatuses).length === 0) return; // Nothing to save
  
    const token = localStorage.getItem('research_helper_token');
  
    try {
      // Send PATCH requests for all edited connections
      const responses = await Promise.all(
        Object.entries(editedStatuses).map(([id, status]) =>
          fetch(`${API_BASE}/user/connections/${id}`, {
            method: 'PATCH',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status }),
          })
        )
      );
  
      // Check for any failed requests
      const failed = responses.filter(res => !res.ok);
      if (failed.length > 0) {
        console.error(`${failed.length} updates failed`);
        alert("Some updates failed. Please try again.");
        return;
      }
  
      // Update local state to reflect saved statuses
      setConnections(prev =>
        prev.map(conn =>
          editedStatuses[conn.id] ? { ...conn, status: editedStatuses[conn.id] } : conn
        )
      );
  
      // Clear edits
      setEditedStatuses({});
  
      // Update stats
      calculateStats(
        connections.map(conn =>
          editedStatuses[conn.id] ? { ...conn, status: editedStatuses[conn.id] } : conn
        )
      );
  
      alert("All statuses saved successfully!");
    } catch (error) {
      console.error("Failed to save statuses:", error);
      alert("An error occurred while saving statuses.");
    }
  };
  
  

  const updateConnectionStatus = async (connectionId: string, status: Connection['status']) => {
    // Optimistically update state
    const updatedConnections = connections.map(conn =>
      conn.id === connectionId ? { ...conn, status } : conn
    );
    setConnections(updatedConnections);
    calculateStats(updatedConnections);
  
    try {
      const token = localStorage.getItem('research_helper_token');
      const response = await fetch(`${API_BASE}/user/connections/${connectionId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status }),
      });
  
      if (!response.ok) {
        throw new Error('Failed to update status on server');
      }
    } catch (error) {
      console.error(error);
      // If API fails, revert back
      fetchConnections();
    }
  };
  

  const deleteConnection = async (connectionId: string) => {
    if (!confirm('Are you sure you want to delete this connection?')) return;
  
    try {
      const token = localStorage.getItem('research_helper_token');
      const response = await fetch(`${API_BASE}/user/connections/${connectionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
  
      if (response.ok) {
        const updatedConnections = connections.filter(conn => conn.id !== connectionId);
        setConnections(updatedConnections);
        calculateStats(updatedConnections);
      } else {
        console.error('Failed to delete connection');
        alert('Failed to delete connection');
      }
    } catch (error) {
      console.error('Failed to delete connection:', error);
      alert('Failed to delete connection');
    }
  };

  const getStatusColor = (status: Connection['status']) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'responded':
        return 'bg-green-100 text-green-800';
      case 'no_response':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status: Connection['status']) => {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'responded':
        return 'Responded';
      case 'no_response':
        return 'No Response';
      default:
        return status;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 pt-20 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Welcome back, {user?.name || user?.email}!
          </h1>
          <p className="text-gray-600 mt-2">
            Track your research connections and manage your outreach efforts <b>(email support in a future update!)</b>
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Mail className="h-6 w-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Connections</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Calendar className="h-6 w-6 text-yellow-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Pending</p>
                <p className="text-2xl font-bold text-gray-900">{stats.pending}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <User className="h-6 w-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Responded</p>
                <p className="text-2xl font-bold text-gray-900">{stats.responded}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-2 bg-red-100 rounded-lg">
                <ExternalLink className="h-6 w-6 text-red-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">No Response</p>
                <p className="text-2xl font-bold text-gray-900">{stats.noResponse}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Connections List */}
        <div className="bg-white rounded-lg shadow">
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-lg font-medium text-gray-900">Your Connections</h2>

              <div className="flex space-x-2">
                <button
                  onClick={saveAllStatuses}
                  className={`px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm ${
                    Object.keys(editedStatuses).length === 0 ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                  disabled={Object.keys(editedStatuses).length === 0}
                >
                  Save All
                </button>

                <a
                  href="/finder"
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-colors"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Find More Professors
                </a>
              </div>
            </div>
          </div>

          {connections.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <School className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No connections yet</h3>
              <p className="text-gray-600 mb-4">
                Start by finding professors in your field and reaching out to them.
              </p>
              <a
                href="/finder"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-colors"
              >
                <Plus className="h-4 w-4 mr-2" />
                Find Professors
              </a>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Professor
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      University
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Field
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date Contacted
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {connections.map((connection) => (
                    <tr key={connection.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {connection.professorName}
                          </div>
                          <div className="text-sm text-gray-500">
                            {connection.email}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {connection.university}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {connection.field}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                      <select
                        value={editedStatuses[connection.id] ?? connection.status}
                        onChange={(e) =>
                          setEditedStatuses(prev => ({ ...prev, [connection.id]: e.target.value as Connection['status'] }))
                        }
                        className={`text-xs font-medium px-2.5 py-0.5 rounded-full border-0 ${getStatusColor(editedStatuses[connection.id] ?? connection.status)}`}
                      >
                        <option value="pending">Pending</option>
                        <option value="responded">Responded</option>
                        <option value="no_response">No Response</option>
                      </select>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {new Date(connection.dateContacted).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <button
                          onClick={() => deleteConnection(connection.id)}
                          className="text-red-600 hover:text-red-900 transition-colors"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UserDashboard;