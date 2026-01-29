"use client";
import React from "react";
import { useEffect, useState } from "react";
import {
  fetchEveryCallData,
  deleteCallRecord,
  updateCallRecord,
} from "../services/calls_services";
import New_call_modal from "../components/New_call_modal";
import Delete_call_modal from "../components/Delete_call_modal";

interface CallData {
  id: number;
  username: string;
  email: string;
  phone: string;
  type: string;
  status: string;
  date: string;
}

const Calls_table = () => {
  const [Call_data_history, setCall_data_history] = useState<CallData[]>([]);
  const [Selected_call, setSelected_call] = useState<CallData | null>(null);
  const [Edit_form, setEdit_form] = useState({
    username: "",
    phone: "",
    email: "",
    type: "",
    date: "",
    time: "",
  });

  //Modal y control del modal
  const [Show_modal, setShow_modal] = useState(false);
  const enable_modal = () => setShow_modal(true);

  // Estados para el modal de eliminación
  const [Show_delete_modal, setShow_delete_modal] = useState(false);

  // Estados para el modal de editar
  const [Is_editing, setIs_editing] = useState(false);

  const enable_editing = (call: CallData) => {
    setSelected_call(call);
    setIs_editing(true);

    setEdit_form({
      username: call.username,
      phone: call.phone,
      email: call.email,
      type: call.type,
      date: call.date.split(" ")[0],
      time: call.date.split(" ")[1]?.trim().substring(0, 5) || "",
    });
  };

  const cancel_selection = () => {
    setSelected_call(null);
    setIs_editing(false);
  };

  //Montura de datos de la BD en el componente
  const fetchCallData = async () => {
    try {
      const data = await fetchEveryCallData();
      setCall_data_history(data);
    } catch (error) {
      console.error("Error al cargar llamadas:", error);
    }
  };

  useEffect(() => {
    fetchCallData();
  }, []);

  const handleDeleteClick = (call: CallData) => {
    setSelected_call(call);
    setIs_editing(false);
    setShow_delete_modal(true);
  };

  const confirmDelete = async () => {
    if (Selected_call) {
      try {
        await deleteCallRecord(Selected_call.id);
        setShow_delete_modal(false);
        fetchCallData();
      } catch (error) {
        alert("No se pudo eliminar el registro");
      }
    }
  };

  //--------------------------------------------Update--------------------------------------------//
  const handleUpdateClick = async (id: number) => {
    try {
      const updatedRecord = {
        username: Edit_form.username,
        email: Edit_form.email,
        phone: Edit_form.phone,
        type: Edit_form.type,
        status: "Agendado",
        date: `${Edit_form.date} ${Edit_form.time}:00`.trim(),
      };

      await updateCallRecord(id, updatedRecord);

      setIs_editing(false);
      setSelected_call(null);
      window.location.reload();
    } catch (error) {
      console.error("Error al actualizar:", error);
      alert("Error al guardar los cambios.");
    }
  };

  const mount_calls_data = () => {
    return Call_data_history && Call_data_history.length > 0 ? (
      Call_data_history.map((item) => {
        const isThisRowEditing = Is_editing && Selected_call?.id === item.id;

        return (
          <React.Fragment key={item.id}>
            {/* FILA PRINCIPAL */}
            <tr
              className={`transition-all duration-200 ${
                isThisRowEditing
                  ? "bg-neutral-secondary-soft ring-1 ring-inset ring-white/50 shadow-lg"
                  : "bg-neutral-primary border-b border-default hover:bg-neutral-secondary-medium/60"
              }`}
            >
              <th
                scope="row"
                className="px-6 py-4 font-medium  text-heading whitespace-nowrap"
              >
                {item.username || "No disponible"}
              </th>
              <td className="px-6 py-4">{item.phone}</td>
              <td className="px-6 py-4">{item.email}</td>
              <td className="px-6 py-4">{item.type}</td>
              <td className="px-6 py-4">
                {item.status === "En curso" ? (
                  <>
                    <>
                      <span className="inline-flex items-center bg-warning-soft border border-warning-subtle text-fg-success-strong text-xs font-medium px-1.5 py-0.5 rounded-sm">
                        <span className="w-2 h-2 me-1 bg-warning rounded-full"></span>
                        {item.status}
                      </span>
                    </>
                  </>
                ) : item.status === "Fallida" ? (
                  <>
                    <>
                      <span className="inline-flex items-center bg-neutral-secondary-medium border border-danger-subtle text-fg-success-strong text-xs font-medium px-1.5 py-0.5 rounded-sm">
                        <span className="w-2 h-2 me-1 bg-gray-900 rounded-full"></span>
                        {item.status}
                      </span>
                    </>
                  </>
                ) : item.status === "Confirmada" ? (
                  <>
                    <span className="inline-flex items-center bg-success-soft border border-success-subtle text-fg-success-strong text-xs font-medium px-1.5 py-0.5 rounded-sm">
                      <span className="w-2 h-2 me-1 bg-success rounded-full"></span>
                      {item.status}
                    </span>
                  </>
                ) : item.status === "Agendado" ? (
                  <>
                    <span className="inline-flex items-center bg-brand-soft border border-brand-subtle text-fg-success-strong text-xs font-medium px-1.5 py-0.5 rounded-sm">
                      <span className="w-2 h-2 me-1 bg-brand rounded-full"></span>
                      {item.status}
                    </span>
                  </>
                ) : (
                  <>
                    <span className="inline-flex items-center bg-danger-soft border border-gray-300 text-fg-success-strong text-xs font-medium px-1.5 py-0.5 rounded-sm">
                      <span className="w-2 h-2 me-1 bg-danger rounded-full"></span>
                      {item.status}
                    </span>
                  </>
                )}
              </td>
              <td className="px-6 py-4">{item.date}</td>
              <td className="px-6 py-4 flex flex-row gap-4">
                {/* Iconos de Eliminar y Editar */}
                <svg
                  className="w-6 h-6 text-red cursor-pointer"
                  onClick={() => handleDeleteClick(item)}
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke="red"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M5 7h14m-9 3v8m4-8v8M10 3h4a1 1 0 0 1 1 1v3H9V4a1 1 0 0 1 1-1ZM6 7h12v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7Z"
                  />
                </svg>

                <svg
                  className={`w-6 h-6 cursor-pointer ${isThisRowEditing ? "text-green-500 animate-pulse" : "text-blue"}`}
                  onClick={() =>
                    isThisRowEditing
                      ? handleUpdateClick(item.id)
                      : enable_editing(item)
                  }
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  {isThisRowEditing ? (
                    <path
                      stroke="currentColor"
                      strokeWidth="2"
                      d="M5 11.917 9.724 16.5 19 7.5"
                    />
                  ) : (
                    <path
                      stroke="#0044b1"
                      strokeWidth="2"
                      d="m14.304 4.844 2.852 2.852M7 7H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h11a1 1 0 0 0 1-1v-4.5m2.409-9.91a2.017 2.017 0 0 1 0 2.853l-6.844 6.844L8 14l.713-3.565 6.844-6.844a2.015 2.015 0 0 1 2.852 0Z"
                    />
                  )}
                </svg>
                {isThisRowEditing && (
                  <svg
                    className="w-6 h-6 text-danger animate-pulse cursor-pointer"
                    aria-hidden="true"
                    xmlns="http://www.w3.org/2000/svg"
                    width="24"
                    height="24"
                    fill="none"
                    viewBox="0 0 24 24"
                    onClick={() => cancel_selection()}
                  >
                    <path
                      stroke="currentColor"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M6 18 17.94 6M18 18 6.06 6"
                    />
                  </svg>
                )}
              </td>
            </tr>
            {/* ACORDEÓN DE EDICIÓN */}
            {isThisRowEditing && (
              <tr
                id={`edit-form-${item.id}`}
                className="bg-gray-200 animate-fadeIn"
              >
                <td
                  colSpan={7}
                  className="px-6 py-4 border-b border-brand-subtle"
                >
                  <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 items-end">
                    {/* Nombre */}
                    <div>
                      <label className="text-[10px] uppercase font-bold text-gray-500 mb-1 block">
                        Nombre
                      </label>
                      <input
                        name="name"
                        type="text"
                        placeholder="Nombre completo"
                        defaultValue={item.username}
                        onChange={(e) =>
                          setEdit_form({
                            ...Edit_form,
                            username: e.target.value,
                          })
                        }
                        className="w-full bg-white/85 border border-white/10 rounded px-2 py-1 text-sm text-black focus:border-brand outline-none"
                      />
                    </div>

                    {/* Teléfono */}
                    <div>
                      <label className="text-[10px] uppercase font-bold text-gray-500 mb-1 block">
                        Teléfono
                      </label>
                      <input
                        name="phone"
                        type="text"
                        placeholder="Teléfono"
                        defaultValue={item.phone}
                        onChange={(e) =>
                          setEdit_form({ ...Edit_form, phone: e.target.value })
                        }
                        className="w-full bg-white/85 border border-white/10 rounded px-2 py-1 text-sm text-black focus:border-brand outline-none"
                      />
                    </div>

                    {/* Correo */}
                    <div>
                      <label className="text-[10px] uppercase font-bold text-gray-500 mb-1 block">
                        Correo
                      </label>
                      <input
                        type="email"
                        placeholder="Correo electrónico"
                        defaultValue={item.email}
                        onChange={(e) =>
                          setEdit_form({ ...Edit_form, email: e.target.value })
                        }
                        className="w-full bg-white/85 border border-white/10 rounded px-2 py-1 text-sm text-black focus:border-brand outline-none"
                      />
                    </div>

                    {/* Categoría */}
                    <div>
                      <label className="text-[10px] uppercase font-bold text-gray-500 mb-1 block">
                        Categoría
                      </label>
                      <select
                        defaultValue={item.type}
                        onChange={(e) =>
                          setEdit_form({ ...Edit_form, type: e.target.value })
                        }
                        className="w-full bg-white/85 border border-white/10 rounded px-2 py-1 text-sm text-black focus:border-brand outline-none"
                      >
                        <option value="Confirmacion">Confirmación</option>
                        <option value="Reagenda">Reagenda</option>
                      </select>
                    </div>

                    {/* Fecha */}
                    <div>
                      <label className="text-[10px] uppercase font-bold text-gray-500 mb-1 block">
                        Fecha
                      </label>
                      <input
                        type="date"
                        defaultValue={item.date.split(" ")[0]}
                        onChange={(e) => setEdit_form({ ...Edit_form, date: e.target.value })}
                        className="w-full bg-white/85 border border-white/10 rounded px-2 py-1 text-sm text-black focus:border-brand outline-none cursor-pointer"
                        style={{ colorScheme: "light" }}
                      />
                    </div>

                    {/* Hora */}
                    <div>
                      <label className="text-[10px] uppercase font-bold text-gray-500 mb-1 block">
                        Hora
                      </label>
                      <input
                        type="time"
                        onChange={(e) => setEdit_form({ ...Edit_form, time: e.target.value })}
                        defaultValue={item.date.split(" ")[1]?.substring(0, 5)}
                        className="w-full bg-white/85 border border-white/10 rounded px-2 py-1 text-sm text-black focus:border-brand outline-none cursor-pointer"
                        style={{ colorScheme: "light" }}
                      />
                    </div>
                  </div>
                </td>
              </tr>
            )}
          </React.Fragment>
        );
      })
    ) : (
      <tr>
        <td colSpan={5} className="px-6 py-4 text-center text-black">
          Cargando datos de llamadas...
        </td>
      </tr>
    );
  };

  const mount_tool_box = () => {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "Space-between",
          alignItems: "center",
          height: "98%",
          margin: "5px",
        }}
      >
        <input
          name="search"
          type="search"
          className="bg-neutral-secondary-medium cursor-pointer border border-default-medium text-black text-sm rounded-base focus:ring-brand focus:border-brand block w-60 px-3 py-2"
          placeholder="Digite para buscar..."
          required
        />
        <button
          type="button"
          className="h-10 inline-flex items-center text-white bg-green-500 hover:bg-green-700 cursor-pointer box-border border border-transparent focus:ring-4 focus:ring-brand-medium shadow-xs font-medium leading-2 rounded-base text-sm px-2 py-2.5 mx-3 focus:outline-none"
          onClick={enable_modal}
        >
          Nueva llamada
          <svg
            className="w-5 h-5 text-gray-800 dark:text-white ml-2"
            aria-hidden="true"
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M7.978 4a2.553 2.553 0 0 0-1.926.877C4.233 6.7 3.699 8.751 4.153 10.814c.44 1.995 1.778 3.893 3.456 5.572 1.68 1.679 3.577 3.018 5.57 3.459 2.062.456 4.115-.073 5.94-1.885a2.556 2.556 0 0 0 .001-3.861l-1.21-1.21a2.689 2.689 0 0 0-3.802 0l-.617.618a.806.806 0 0 1-1.14 0l-1.854-1.855a.807.807 0 0 1 0-1.14l.618-.62a2.692 2.692 0 0 0 0-3.803l-1.21-1.211A2.555 2.555 0 0 0 7.978 4Z" />
          </svg>
        </button>
      </div>
    );
  };

  return (
    <div
      style={{
        display: "grid",
        gridTemplateRows: "8% 1fr",
        gap: "5px",
        height: "100%",
        padding: "5px",
        backgroundColor: "rgb(0, 10, 51)",
      }}
    >
      <div>{mount_tool_box()}</div>
      <div className="relative overflow-x-auto bg-neutral-primary-soft shadow-xs border border-default p-3">
        <table className="w-full text-sm text-left rtl:text-right text-body">
          <thead className="text-sm text-body bg-neutral-secondary-soft border-b rounded-base border-default">
            <tr>
              <th scope="col" className="px-6 py-3 font-medium">
                Nombre
              </th>
              <th scope="col" className="px-6 py-3 font-medium">
                Telefono
              </th>
              <th scope="col" className="px-6 py-3 font-medium">
                Correo
              </th>
              <th scope="col" className="px-6 py-3 font-medium">
                Categoria
              </th>
              <th scope="col" className="px-6 py-3 font-medium">
                Estado
              </th>
              <th scope="col" className="px-6 py-3 font-medium">
                Fecha
              </th>
              <th scope="col" className="px-6 py-3"></th>
            </tr>
          </thead>
          <tbody>{mount_calls_data()}</tbody>
        </table>
      </div>
      {/* Modales */}
      {Show_modal && <New_call_modal onClose={() => setShow_modal(false)} />}

      {Show_delete_modal && Selected_call && (
        <Delete_call_modal
          username={Selected_call.username}
          onClose={() => setShow_delete_modal(false)}
          onConfirm={confirmDelete}
        />
      )}
    </div>
  );
};

export default Calls_table;
