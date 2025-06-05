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

function KnowledgeBase() {
  const [entries, setEntries] = useState([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [newEntry, setNewEntry] = useState({
    question: '',
    answer: '',
    confidence: 1.0,
  });
  const [ws, setWs] = useState(null);

  const columns = [
    { field: 'question', headerName: 'Question', width: 300 },
    { field: 'answer', headerName: 'Answer', width: 400 },
    { field: 'confidence', headerName: 'Confidence', width: 120 },
    { field: 'last_updated', headerName: 'Last Updated', width: 180 },
  ];

  useEffect(() => {
    fetchEntries();
    
    // Set up WebSocket connection
    const websocket = new WebSocket('ws://localhost:8000/ws');
    setWs(websocket);

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'knowledge_update') {
        fetchEntries(); // Refresh entries when knowledge base is updated
      }
    };

    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, []);

const fetchEntries = async () => {
  try {
    const response = await axios.get('http://localhost:8000/knowledge-base/');
    // Add a unique id to each entry (use last_updated + question as a fallback)
    const entriesWithId = response.data.map((entry, idx) => ({
      ...entry,
      id: entry.id || `${entry.question}-${entry.last_updated || idx}`
    }));
    setEntries(entriesWithId);
  } catch (error) {
    console.error('Error fetching knowledge base entries:', error);
  }
};

  const handleOpenDialog = () => {
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setNewEntry({
      question: '',
      answer: '',
      confidence: 1.0,
    });
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewEntry((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async () => {
    if (!newEntry.question || !newEntry.answer) return;

    try {
      await axios.post('http://localhost:8000/knowledge-base/', newEntry);
      await fetchEntries();
      handleCloseDialog();
    } catch (error) {
      console.error('Error adding knowledge base entry:', error);
    }
  };

  return (
    <Box sx={{ height: 600, width: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h4">Knowledge Base</Typography>
        <Button variant="contained" color="primary" onClick={handleOpenDialog}>
          Add Entry
        </Button>
      </Box>

      <DataGrid
        rows={entries}
        columns={columns}
        pageSize={10}
        rowsPerPageOptions={[10]}
        checkboxSelection
        disableSelectionOnClick
      />

      <Dialog open={openDialog} onClose={handleCloseDialog}>
        <DialogTitle>Add Knowledge Base Entry</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            name="question"
            label="Question"
            fullWidth
            value={newEntry.question}
            onChange={handleInputChange}
          />
          <TextField
            margin="dense"
            name="answer"
            label="Answer"
            fullWidth
            multiline
            rows={4}
            value={newEntry.answer}
            onChange={handleInputChange}
          />
          <TextField
            margin="dense"
            name="confidence"
            label="Confidence"
            type="number"
            fullWidth
            value={newEntry.confidence}
            onChange={handleInputChange}
            inputProps={{ min: 0, max: 1, step: 0.1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained" color="primary">
            Add
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default KnowledgeBase; 