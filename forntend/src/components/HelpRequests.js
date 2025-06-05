import React, { useState, useEffect } from 'react';
import { DataGrid } from '@mui/x-data-grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import axios from 'axios';

function HelpRequests() {
  const [requests, setRequests] = useState([]);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [response, setResponse] = useState('');
  const [openDialog, setOpenDialog] = useState(false);
  const [ws, setWs] = useState(null);

  const columns = [
    { field: 'id', headerName: 'ID', width: 90 },
    { field: 'caller_details', headerName: 'Caller', width: 150 },
    { field: 'question', headerName: 'Question', width: 300 },
    { field: 'status', headerName: 'Status', width: 120 },
    { field: 'timestamp', headerName: 'Timestamp', width: 180 },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 150,
      renderCell: (params) => (
        <Button
          variant="contained"
          color="primary"
          size="small"
          onClick={() => handleResponse(params.row)}
        >
          Respond
        </Button>
      ),
    },
  ];

  useEffect(() => {
    fetchRequests();
    
    // Set up WebSocket connection
    const websocket = new WebSocket('ws://localhost:8000/ws');
    setWs(websocket);

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'new_request') {
        setRequests((prevRequests) => [...prevRequests, data.data]);
      }
    };

    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, []);

  const fetchRequests = async () => {
    try {
      const response = await axios.get('http://localhost:8000/help-requests/');
      setRequests(response.data);
    } catch (error) {
      console.error('Error fetching requests:', error);
    }
  };

  const handleResponse = (request) => {
    setSelectedRequest(request);
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setSelectedRequest(null);
    setResponse('');
  };

  const handleSubmitResponse = async () => {
    if (!selectedRequest || !response) return;

    try {
      await axios.put(`http://localhost:8000/help-requests/${selectedRequest.id}`, {
        status: 'resolved',
        supervisor_response: response,
      });

      // Update local state
      setRequests((prevRequests) =>
        prevRequests.map((req) =>
          req.id === selectedRequest.id
            ? { ...req, status: 'resolved', supervisor_response: response }
            : req
        )
      );

      handleCloseDialog();
    } catch (error) {
      console.error('Error submitting response:', error);
    }
  };

  return (
    <Box sx={{ height: 600, width: '100%' }}>
      <Typography variant="h4" gutterBottom>
        Help Requests
      </Typography>
      
      <DataGrid
        rows={requests}
        columns={columns}
        pageSize={10}
        rowsPerPageOptions={[10]}
        checkboxSelection
        disableSelectionOnClick
      />

      <Dialog open={openDialog} onClose={handleCloseDialog}>
        <DialogTitle>Respond to Request</DialogTitle>
        <DialogContent>
          <Typography variant="subtitle1" gutterBottom>
            Question: {selectedRequest?.question}
          </Typography>
          <TextField
            autoFocus
            margin="dense"
            label="Your Response"
            fullWidth
            multiline
            rows={4}
            value={response}
            onChange={(e) => setResponse(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSubmitResponse} variant="contained" color="primary">
            Submit
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default HelpRequests; 