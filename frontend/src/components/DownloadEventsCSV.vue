<template>
    <el-button type="primary" @click="downloadEventsCsv"<el-icon><Download /></el-icon>>Download</el-button>
</template>
<script>
import { Download } from '@element-plus/icons-vue';
import axios from 'axios';
export default {
   name: "DownloadEventsCSV",
   components: {
        Download
   },
   methods: {
        async downloadEventsCsv(){
            try {
                // Make an axios GET request to the Flask backend to get the CSV file
                const response = await axios({
                url: 'http://127.0.0.1:5000/download-events-csv', // URL to Flask backend
                method: 'GET',
                responseType: 'blob' // Important to handle binary response (CSV)
                });

                // Create a link element, use the URL.createObjectURL for the response
                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', 'confirmed_events.xlsx'); // Set the download filename
                document.body.appendChild(link);
                link.click();

                // Clean up and remove the link after download
                link.remove();
            } catch (error) {
                console.error('Error downloading the file:', error);
            }

        }
   }

}
</script>