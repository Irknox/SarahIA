import axios from "axios";


const IS_PROD = true; 

const BASE_URL = IS_PROD 
  ? "http://64.23.170.136/SchedulerAgent/API" 
  : "http://localhost:7676";
  
const getUrl = (path) => {
  if (IS_PROD) return `${BASE_URL}${path}`;
  return `${BASE_URL}${path}/dev`;
};

export const fetchEveryCallData = async () => {
  try {
    const response = await axios.get(`${BASE_URL}/calls`, {
      headers: { auth_token: process.env.AUTH_TOKEN }
    });
    return response.data;
  } catch (error) {
    console.error("Error fetching calls:", error);
    throw error;
  }
};

export const addCallRecord = async (callData) => {
  try {
    const url = IS_PROD ? `${BASE_URL}/calls/add` : `${BASE_URL}/calls/add/dev`;
    const response = await axios.post(url, callData, {
      headers: {
        "Content-Type": "application/json",
        auth_token: process.env.AUTH_TOKEN,
      },
    });
    return response.data;
  } catch (error) {
    console.error("Error adding record:", error);
    throw error;
  }
};

export const updateCallRecord = async (callId, callData) => {
  try {
    const url = getUrl(`/calls/update/${callId}`);
    const response = await axios.put(url, callData, {
      headers: {
        "Content-Type": "application/json",
        auth_token: process.env.AUTH_TOKEN,
      },
    });
    return response.data;
  } catch (error) {
    console.error("Error updating record:", error);
    throw error;
  }
};

export const deleteCallRecord = async (callId) => {
  try {
    const url = getUrl(`/calls/delete/${callId}`);
    const response = await axios.delete(url, {
      headers: { auth_token: process.env.AUTH_TOKEN },
    });
    return response.data;
  } catch (error) {
    console.error("Error deleting record:", error);
    throw error;
  }
};