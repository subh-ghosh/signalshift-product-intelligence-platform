import { PieChart, Pie, Cell, Tooltip, Legend } from "recharts"
import { useEffect, useState } from "react"
import api from "../services/api"

export default function SentimentChart(){

  const [data,setData] = useState([])
  const [loading,setLoading] = useState(true)

  useEffect(()=>{

    api.get("/dashboard/sentiment").then(res=>{

      const formatted = [
        {name:"positive", value:res.data.positive},
        {name:"negative", value:res.data.negative}
      ]

      setData(formatted)
      setLoading(false)

    }).catch(()=>{
      setLoading(false)
    })

  },[])

  if(loading) return <p>Loading sentiment data...</p>

  return(

    <PieChart width={400} height={300}>

      <Pie
        data={data}
        dataKey="value"
        nameKey="name"
        outerRadius={100}
        label
      >

        <Cell fill="#4CAF50"/>
        <Cell fill="#F44336"/>

      </Pie>

      <Tooltip/>
      <Legend/>

    </PieChart>

  )
}