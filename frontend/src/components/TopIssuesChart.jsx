import {
 BarChart,
 Bar,
 XAxis,
 YAxis,
 Tooltip,
 CartesianGrid,
 ResponsiveContainer
} from "recharts"

import { useEffect,useState } from "react"
import api from "../services/api"

export default function TopIssuesChart({onIssueClick}){

 const [data,setData] = useState([])
 const [loading,setLoading] = useState(true)

 useEffect(()=>{

  const fetchIssues = async () => {

   try{

    const res = await api.get("/dashboard/top-issues")

    setData(res.data || [])

   }catch(err){

    console.error("Failed to load issues",err)

   }finally{

    setLoading(false)

   }

  }

  fetchIssues()

 },[])


 const handleClick = (entry) => {

  if(!entry || !entry.issue) return

  if(onIssueClick){

   onIssueClick(entry.issue)

  }

 }


 if(loading){
  return <p>Loading issues...</p>
 }


 return(

  <div style={{width:"100%",height:400}}>

   <ResponsiveContainer>

    <BarChart
     data={data}
     layout="vertical"
     margin={{top:20,right:30,left:20,bottom:20}}
    >

     <CartesianGrid strokeDasharray="3 3"/>

     <XAxis type="number"/>

     <YAxis
      type="category"
      dataKey="issue"
      width={250}
     />

     <Tooltip/>

     <Bar
      dataKey="mentions"
      fill="#4CAF50"
      onClick={(entry)=>handleClick(entry)}
      cursor="pointer"
     />

    </BarChart>

   </ResponsiveContainer>

  </div>

 )
}