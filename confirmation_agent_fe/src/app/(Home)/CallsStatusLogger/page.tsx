import Calls_table from "../../../components/Calls_table";
import General_Nav from "../../../components/General_Nav";

export default function CallStatusLog() {
  return (
    <div style={{ display: "grid", gridTemplate: "60px 1fr/ 1fr",height:"100vh" }}>
      <General_Nav />

      <Calls_table />
    </div>
  );
}
