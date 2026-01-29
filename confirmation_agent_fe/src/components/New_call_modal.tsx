"use client";

import React, { useState } from "react";
import { addCallRecord } from "../services/calls_services";

interface ModalProps {
  onClose: () => void;
}

const New_call_modal = ({ onClose }: ModalProps) => {
  const [formData, setFormData] = useState({
    username: "",
    phone: "",
    email: "",
    type: "Confirmacion",
    date: new Date().toISOString().split("T")[0],
    time: "",
  });

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const callToSave = {
        username: formData.username,
        phone: formData.phone,
        email: formData.email,
        type: formData.type,
        status: "Agendado",
        date: `${formData.date} ${formData.time}:00`, 
      };

      await addCallRecord(callToSave);
      onClose();
      window.location.reload();
    } catch (error) {
      alert("Error al guardar la llamada");
    }
  };

  return (
    <div
      style={{
        position: "fixed", top: 0, left: 0, width: "100vw", height: "100vh",
        backgroundColor: "rgba(0, 0, 0, 0.75)", display: "flex",
        justifyContent: "center", alignItems: "center", zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        className="bg-[#0e344f] border border-default p-8 rounded-lg shadow-xl"
        style={{ width: "40vw", minWidth: "350px", maxHeight: "90vh", overflowY: "auto" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white">Agendar Llamada</h2>
          <button onClick={onClose} className="text-white hover:text-brand">✕</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 mb-4 md:grid-cols-2">
            <div>
              <label className="block mb-2 text-sm font-medium text-white">Nombre</label>
              <input
                name="username"
                type="text"
                value={formData.username}
                onChange={handleChange}
                className="bg-neutral-secondary-medium border border-default-medium text-black text-sm rounded-base focus:ring-brand focus:border-brand block w-full px-3 py-2"
                placeholder="Nombre"
                required
              />
            </div>

            <div>
              <label className="block mb-2 text-sm font-medium text-white">Teléfono</label>
              <input
                name="phone"
                type="tel"
                value={formData.phone}
                onChange={handleChange}
                className="bg-neutral-secondary-medium border border-default-medium text-black text-sm rounded-base focus:ring-brand focus:border-brand block w-full px-3 py-2"
                placeholder="12345678"
                required
              />
            </div>

            <div>
              <label className="block mb-2 text-sm font-medium text-white">Fecha</label>
              <input
                name="date"
                type="date"
                value={formData.date}
                onChange={handleChange}
                className="bg-neutral-secondary-medium border border-default-medium text-black text-sm rounded-base focus:ring-brand focus:border-brand block w-full px-3 py-2 cursor-pointer"
                style={{ colorScheme: "light" }}
                required
              />
            </div>

            <div>
              <label className="block mb-2 text-sm font-medium text-white">Hora</label>
              <input
                name="time"
                type="time"
                value={formData.time}
                onChange={handleChange}
                className="bg-neutral-secondary-medium border border-default-medium text-black text-sm rounded-base focus:ring-brand focus:border-brand block w-full px-3 py-2 cursor-pointer"
                style={{ colorScheme: "light" }}
                required
              />
            </div>
          </div>

          <div className="mb-4">
            <label className="block mb-2 text-sm font-medium text-white">Categoría</label>
            <select
              name="type"
              value={formData.type}
              onChange={handleChange}
              className="bg-neutral-secondary-medium border border-default-medium text-black text-sm rounded-base focus:ring-brand focus:border-brand block w-full px-3 py-2"
            >
              <option value="Confirmacion">Confirmación</option>
              <option value="Reagenda">Reagenda</option>
            </select>
          </div>

          <div className="mb-6">
            <label className="block mb-2 text-sm font-medium text-white">Correo electrónico</label>
            <input
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              className="bg-neutral-secondary-medium border border-default-medium text-black text-sm rounded-base focus:ring-brand focus:border-brand block w-full px-3 py-2"
              placeholder="ejemplo@correo.com"
              required
            />
          </div>

          <div className="flex gap-3">
            <button type="submit" className="flex-1 text-white bg-brand hover:bg-brand-strong font-medium rounded-base text-sm px-4 py-2.5 transition-colors">Confirmar</button>
            <button type="button" onClick={onClose} className="flex-1 text-white bg-gray-600 hover:bg-gray-700 font-medium rounded-base text-sm px-4 py-2.5 transition-colors">Cancelar</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default New_call_modal;