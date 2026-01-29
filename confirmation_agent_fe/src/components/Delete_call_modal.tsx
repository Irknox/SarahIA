"use client";

import React from "react";

interface DeleteModalProps {
  onClose: () => void;
  onConfirm: () => void;
  username: string;
}

const Delete_call_modal = ({ onClose, onConfirm, username }: DeleteModalProps) => {
  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-[#0e344f] border border-red-900/50 p-6 rounded-lg shadow-2xl w-[300px] text-center"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-white text-sm mb-4">
          ¿Seguro que deseas eliminar el registro de <strong>{username}</strong>?
        </p>
        <div className="flex gap-2">
          <button
            onClick={onConfirm}
            className="flex-1 bg-red-700 hover:bg-red-800 text-white text-xs py-2 rounded-base transition-colors"
          >
            Sí, eliminar
          </button>
          <button
            onClick={onClose}
            className="flex-1 bg-gray-600 hover:bg-gray-700 text-white text-xs py-2 rounded-base transition-colors"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
};

export default Delete_call_modal;