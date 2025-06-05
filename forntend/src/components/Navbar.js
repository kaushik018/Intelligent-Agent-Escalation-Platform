import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  LibraryBooks as KnowledgeIcon,
  Help as HelpIcon,
  VideoCall as LiveKitIcon,
  KeyboardArrowDown as ArrowDownIcon,
} from '@mui/icons-material';

function Navbar() {
  const [anchorEl, setAnchorEl] = React.useState(null);
  const open = Boolean(anchorEl);

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Salon AI Receptionist
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            color="inherit"
            component={RouterLink}
            to="/"
            startIcon={<DashboardIcon />}
          >
            Dashboard
          </Button>
          <Button
            color="inherit"
            onClick={handleClick}
            startIcon={<KnowledgeIcon />}
            endIcon={<ArrowDownIcon />}
          >
            Knowledge Base
          </Button>
          <Menu
            anchorEl={anchorEl}
            open={open}
            onClose={handleClose}
          >
            <MenuItem
              component={RouterLink}
              to="/knowledge-base/predefined"
              onClick={handleClose}
            >
              Predefined Knowledge
            </MenuItem>
            <MenuItem
              component={RouterLink}
              to="/knowledge-base/learned"
              onClick={handleClose}
            >
              Learned Knowledge
            </MenuItem>
          </Menu>
          <Button
            color="inherit"
            component={RouterLink}
            to="/help-requests"
            startIcon={<HelpIcon />}
          >
            Help Requests
          </Button>
          <Button
            color="inherit"
            component={RouterLink}
            to="/livekit"
            startIcon={<LiveKitIcon />}
          >
            LiveKit Room
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default Navbar; 