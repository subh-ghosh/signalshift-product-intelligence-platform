import { useState } from "react"
import api from "../services/api"

import SentimentChart from "../components/SentimentChart"
import TopIssuesChart from "../components/TopIssuesChart"

export default function Dashboard(){

 const [file,setFile] = useState(null)
 const [status,setStatus] = useState("")
 const [reviews,setReviews] = useState([])
 const [issue,setIssue] = useState("")
 const [loading,setLoading] = useState(false)

 const handleUpload = async () => {

  if(!file){
   setStatus("Please select a file")
   return
  }

  const formData = new FormData()
  formData.append("file",file)

  try{

   setLoading(true)

   await api.post("/upload-reviews",formData)

   setStatus("Upload successful")

  }catch(err){

   console.error(err)

   setStatus("Upload failed")

  }finally{

   setLoading(false)

  }

 }


 const handleIssueClick = async (keywords) => {

  try{

   setLoading(true)

   setIssue(keywords)

   const res = await api.get("/dashboard/issue-reviews",{
    params:{issue:keywords}
   })

   setReviews(res.data.reviews || [])

  }catch(err){

   console.error(err)

   setReviews([])

  }finally{

   setLoading(false)

  }

 }


 return(

  <div style={{padding:"40px",maxWidth:"1200px",margin:"auto"}}>

   <h1>Netflix Dashboard</h1>

   {/* Upload Section */}

   <h2>Upload Latest Reviews</h2>

   <input
    type="file"
    onChange={(e)=>setFile(e.target.files[0])}
   />

   <button
    onClick={handleUpload}
    disabled={loading}
    style={{marginLeft:"10px"}}
   >
    Upload
   </button>

   <p>{status}</p>

   <hr/>

   {/* Sentiment Chart */}

   <h2>Sentiment Distribution</h2>

   <SentimentChart/>

   <hr/>

   {/* Top Issues */}

   <h2>Top Issues</h2>

   <TopIssuesChart onIssueClick={handleIssueClick}/>

   <hr/>

   {/* Reviews */}

   {loading && <p>Loading reviews...</p>}

   {reviews.length > 0 && (

    <div>

     <h3>Reviews for: {issue}</h3>

     <ul style={{
      maxHeight:"300px",
      overflowY:"auto",
      border:"1px solid #ddd",
      padding:"10px"
     }}>

      {reviews.map((r,i)=>(
       <li key={i} style={{marginBottom:"10px"}}>
        {r}
       </li>
      ))}

     </ul>

    </div>

   )}

  </div>

 )
}