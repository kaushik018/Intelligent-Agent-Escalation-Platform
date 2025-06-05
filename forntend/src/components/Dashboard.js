import React, { useState, useEffect } from 'react';
import { Grid, Paper, Typography, Box } from '@mui/material';
import axios from 'axios';

function Dashboard() {
  const [stats, setStats] = useState({
    totalRequests: 0,
    pendingRequests: 0,
    resolvedRequests: 0,
    knowledgeBaseEntries: 0,
  });

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const [requestsResponse, kbResponse] = await Promise.all([
        axios.get('http://localhost:8000/help-requests/'),
        axios.get('http://localhost:8000/knowledge-base/'),
      ]);

      const requests = requestsResponse.data;
      const knowledgeBaseEntries = kbResponse.data;

      setStats({
        totalRequests: requests.length,
        pendingRequests: requests.filter((r) => r.status === 'pending').length,
        resolvedRequests: requests.filter((r) => r.status === 'resolved').length,
        knowledgeBaseEntries: knowledgeBaseEntries.length,
      });
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
    }
  };

  const StatCard = ({ title, value, color }) => (
    <Paper
      sx={{
        p: 3,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        backgroundColor: color,
        color: 'white',
      }}
    >
      <Typography variant="h6" component="div">
        {title}
      </Typography>
      <Typography variant="h3" component="div">
        {value}
      </Typography>
    </Paper>
  );

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Requests"
            value={stats.totalRequests}
            color="#1976d2"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Pending Requests"
            value={stats.pendingRequests}
            color="#f57c00"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Resolved Requests"
            value={stats.resolvedRequests}
            color="#388e3c"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Knowledge Base Entries"
            value={stats.knowledgeBaseEntries}
            color="#7b1fa2"
          />
        </Grid>
      </Grid>

      <Box sx={{ mt: 4 }}>
        <Typography variant="h5" gutterBottom>
          System Status
        </Typography>
        <Paper sx={{ p: 3 }}>
          <Typography variant="body1">
            The AI receptionist system is running and ready to handle customer calls.
            The system will automatically escalate to human supervisors when needed.
          </Typography>
        </Paper>
      </Box>
    </Box>
  );
}

export default Dashboard; 