from flask import Flask, request, render_template_string, send_file, redirect, url_for, jsonify
import os
import shutil
import stat
import zipfile
import tarfile
import gzip
import io
import math
import mimetypes

app = Flask(__name__)

BASE_DIR = os.path.expanduser("~")

LARGE_FILE_THRESHOLD_BYTES = 1024 * 1024 * 5
CHUNK_SIZE_LINES = 5000

HTML_TEMPLATE = '''
<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Termux Файловый Менеджер</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css" crossorigin="anonymous" referrerpolicy="no-referrer" />
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f3f4f6;
            color: #374151;
        }
        .container {
            max-width: 95%;
            margin: 1rem auto;
            padding: 1rem;
            background-color: #ffffff;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .btn {
            @apply px-3 py-1.5 rounded-lg font-semibold text-white transition duration-200 ease-in-out flex items-center justify-center text-sm;
        }
        .btn-primary {
            @apply bg-blue-600 hover:bg-blue-700;
        }
        .btn-danger {
            @apply bg-red-600 hover:bg-red-700;
        }
        .btn-info {
            @apply bg-gray-600 hover:bg-gray-700;
        }
        .btn-success {
            @apply bg-green-600 hover:bg-green-700;
        }
        .input-field {
            @apply px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm;
        }
        .file-list li {
            @apply flex flex-wrap items-center justify-between py-2 border-b border-gray-200 last:border-b-0;
        }
        .file-list li a {
            @apply text-blue-600 hover:underline;
        }
        .file-list li span {
            @apply text-gray-800;
        }
        .action-buttons {
            @apply flex flex-wrap justify-end items-center mt-2 md:mt-0;
        }
        .action-buttons button, .action-buttons a {
            @apply ml-1 md:ml-2 text-xs btn-info px-2 py-1 mb-1;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0,0,0,0.4);
            justify-content: center;
            align-items: center;
            padding: 0.5rem;
        }
        .modal-content {
            background-color: #fefefe;
            margin: auto;
            padding: 15px;
            border-radius: 0.75rem;
            width: 98%;
            max-width: 800px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            position: relative;
            transform: translateY(-50px);
            opacity: 0;
            animation: slideIn 0.3s forwards ease-out;
        }
        @keyframes slideIn {
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        .close-button {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        .close-button:hover,
        .close-button:focus {
            color: black;
            text-decoration: none;
        }
        textarea {
            width: 100%;
            height: 400px;
            border: 1px solid #ccc;
            padding: 10px;
            font-family: monospace;
            resize: vertical;
            border-radius: 0.5rem;
            font-size: 0.875rem;
        }
        .message-box {
            position: fixed;
            top: 10px;
            right: 10px;
            background-color: #4CAF50;
            color: white;
            padding: 10px;
            border-radius: 5px;
            z-index: 1001;
            display: none;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            animation: fadeInOut 3s forwards;
            font-size: 0.875rem;
        }
        .message-box.error {
            background-color: #f44336;
        }
        @keyframes fadeInOut {
            0% { opacity: 0; transform: translateY(-20px); }
            10% { opacity: 1; transform: translateY(0); }
            90% { opacity: 1; transform: translateY(0); }
            100% { opacity: 0; transform: translateY(-20px); }
        }
        .loading-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            z-index: 1002;
            justify-content: center;
            align-items: center;
            flex-direction: column;
            color: white;
            font-size: 1.25rem;
        }
        .spinner {
            border: 6px solid rgba(255, 255, 255, 0.3);
            border-top: 6px solid #3498db;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin-bottom: 0.75rem;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @media (max-width: 768px) {
            .grid-cols-1\.5 {
                grid-template-columns: 1fr;
            }
            .action-buttons {
                justify-content: flex-start;
                width: 100%;
            }
            .action-buttons button, .action-buttons a {
                margin-left: 0;
                margin-right: 0.25rem;
                padding: 0.25rem 0.5rem;
                font-size: 0.65rem;
            }
            .file-list li {
                flex-direction: column;
                align-items: flex-start;
            }
            .file-list li > *:not(.action-buttons) {
                width: 100%;
                margin-bottom: 0.25rem;
            }
            .file-list li span.flex-grow {
                margin-bottom: 0;
            }
            .modal-content h2 {
                font-size: 1.1rem;
            }
            .modal-content p {
                font-size: 0.9rem;
            }
            .input-field {
                font-size: 0.8rem;
            }
        }
        .drop-zone {
            border: 2px dashed #cbd5e1;
            border-radius: 0.5rem;
            padding: 1rem;
            text-align: center;
            color: #64748b;
            transition: all 0.2s ease-in-out;
            font-size: 0.875rem;
        }
        .drop-zone.highlight {
            border-color: #3b82f6;
            background-color: #eff6ff;
            color: #2563eb;
        }
    </style>
</head>
<body class="p-4">
    <div class="container">
        <h1 class="text-2xl md:text-3xl font-bold mb-4 md:mb-6 text-center">📂 Файловый Менеджер</h1>

        <div class="mb-4 md:mb-6">
            <h2 class="text-lg md:text-xl font-semibold mb-2">Текущий Путь: <span class="text-blue-700 break-all">{{ path }}</span></h2>
            <form method="get" action="/" class="flex flex-col md:flex-row space-y-2 md:space-y-0 md:space-x-2">
                <input type="text" name="path" placeholder="Перейти к пути" value="{{ path }}" class="input-field flex-grow">
                <button type="submit" class="btn btn-primary"><i class="fas fa-arrow-right mr-2"></i> Перейти</button>
            </form>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 md:mb-6">
            <div class="bg-gray-50 p-4 rounded-lg shadow-sm">
                <h3 class="text-base md:text-lg font-semibold mb-2">Загрузить Файл</h3>
                <form id="uploadForm" action="/upload" method="post" enctype="multipart/form-data" class="flex flex-col space-y-3">
                    <input type="hidden" name="path" value="{{ path }}">
                    <input type="file" name="file" class="input-field bg-white">
                    <button type="submit" class="btn btn-success"><i class="fas fa-upload mr-2"></i> Загрузить</button>
                </form>
                <div id="dropZone" class="drop-zone mt-4">
                    <p>Перетащите файлы сюда для загрузки</p>
                </div>
            </div>

            <div class="bg-gray-50 p-4 rounded-lg shadow-sm">
                <h3 class="text-base md:text-lg font-semibold mb-2">Создать Новую Папку</h3>
                <form action="/create_folder" method="post" class="flex flex-col space-y-3">
                    <input type="hidden" name="current_path" value="{{ path }}">
                    <input type="text" name="folder_name" placeholder="Имя папки" class="input-field" required>
                    <button type="submit" class="btn btn-primary"><i class="fas fa-folder-plus mr-2"></i> Создать Папку</button>
                </form>
            </div>

            <div class="bg-gray-50 p-4 rounded-lg shadow-sm">
                <h3 class="text-base md:text-lg font-semibold mb-2">Создать Новый Файл</h3>
                <form action="/create_file" method="post" class="flex flex-col space-y-3">
                    <input type="hidden" name="current_path" value="{{ path }}">
                    <input type="text" name="file_name" placeholder="Имя файла" class="input-field" required>
                    <button type="submit" class="btn btn-primary"><i class="fas fa-file-circle-plus mr-2"></i> Создать Файл</button>
                </form>
            </div>

            <div class="bg-gray-50 p-4 rounded-lg shadow-sm">
                <h3 class="text-base md:text-lg font-semibold mb-2">Поиск</h3>
                <input type="text" id="searchInput" onkeyup="filterList()" placeholder="Поиск по имени..." class="input-field w-full">
            </div>
        </div>

        <h3 class="text-lg md:text-xl font-semibold mb-4">Содержимое:</h3>
        <ul class="file-list" id="fileList">
            {% if parent %}
                <li>
                    <a href="/?path={{ parent }}" class="flex items-center">
                        <span class="mr-2 text-xl"><i class="fas fa-arrow-up"></i></span> ..
                    </a>
                </li>
            {% endif %}
            {% for item in items %}
                <li data-name="{{ item.name | lower }}">
                    {% if item.isdir %}
                        <a href="/?path={{ item.path }}" class="flex items-center flex-grow">
                            <span class="mr-2 text-xl"><i class="fas fa-folder text-yellow-500"></i></span> {{ item.name }}
                            <span class="ml-4 text-gray-500 text-xs font-mono">{{ item.permissions }}</span>
                        </a>
                        <div class="action-buttons">
                            <button onclick="showRenamePrompt('{{ item.path }}', '{{ item.name }}')" class="btn btn-info"><i class="fas fa-pen mr-1"></i> Переименовать</button>
                            <button onclick="showMoveCopyPrompt('{{ item.path }}', 'move')" class="btn btn-info"><i class="fas fa-arrows-alt mr-1"></i> Переместить</button>
                            <button onclick="showMoveCopyPrompt('{{ item.path }}', 'copy')" class="btn btn-info"><i class="fas fa-copy mr-1"></i> Копировать</button>
                            <button onclick="confirmAction('/delete?path={{ item.path }}&back={{ path }}', 'Вы уверены, что хотите удалить папку \\'{{ item.name }}\\', включая ее содержимое?')" class="btn btn-danger"><i class="fas fa-trash-alt mr-1"></i> Удалить</button>
                        </div>
                    {% elif item.is_archive %}
                        <span class="flex items-center flex-grow">
                            <span class="mr-2 text-xl"><i class="fas fa-file-archive text-purple-500"></i></span> {{ item.name }}
                            <span class="ml-2 text-gray-500 text-sm">({{ item.size }})</span>
                            <span class="ml-4 text-gray-500 text-xs font-mono">{{ item.permissions }}</span>
                        </span>
                        <div class="action-buttons">
                            <button onclick="openArchiveModal('{{ item.path }}')" class="btn btn-info"><i class="fas fa-box-open mr-1"></i> Просмотреть Архив</button>
                            <button onclick="showRenamePrompt('{{ item.path }}', '{{ item.name }}')" class="btn btn-info"><i class="fas fa-pen mr-1"></i> Переименовать</button>
                            <button onclick="showMoveCopyPrompt('{{ item.path }}', 'move')" class="btn btn-info"><i class="fas fa-arrows-alt mr-1"></i> Переместить</button>
                            <button onclick="showMoveCopyPrompt('{{ item.path }}', 'copy')" class="btn btn-info"><i class="fas fa-copy mr-1"></i> Копировать</button>
                            <button onclick="confirmAction('/delete?path={{ item.path }}&back={{ path }}', 'Вы уверены, что хотите удалить архив \\'{{ item.name }}\\'?')" class="btn btn-danger"><i class="fas fa-trash-alt mr-1"></i> Удалить</button>
                        </div>
                    {% else %}
                        <span class="flex items-center flex-grow">
                            <span class="mr-2 text-xl">
                                {% if item.is_image %}
                                    <i class="fas fa-image text-green-500"></i>
                                {% elif item.is_text %}
                                    <i class="fas fa-file-alt text-blue-500"></i>
                                {% else %}
                                    <i class="fas fa-file text-gray-500"></i>
                                {% endif %}
                            </span> {{ item.name }}
                            <span class="ml-2 text-gray-500 text-sm">({{ item.size }})</span>
                            <span class="ml-4 text-gray-500 text-xs font-mono">{{ item.permissions }}</span>
                        </span>
                        <div class="action-buttons">
                            <a href="/download?path={{ item.path }}" class="btn btn-info"><i class="fas fa-download mr-1"></i> Скачать</a>
                            {% if item.is_image %}
                                <button onclick="openImagePreviewModal('{{ item.path }}')" class="btn btn-info"><i class="fas fa-eye mr-1"></i> Просмотреть</button>
                            {% elif item.is_text %}
                                {% if item.is_large_text %}
                                    <button onclick="openLargeFileViewerModal('{{ item.path }}', 1)" class="btn btn-info"><i class="fas fa-eye mr-1"></i> Просмотреть (Большой файл)</button>
                                    <a href="/download?path={{ item.path }}" class="btn btn-info"><i class="fas fa-download mr-1"></i> Скачать для Редактирования</a>
                                {% else %}
                                    <button onclick="openEditModal('{{ item.path }}')" class="btn btn-info"><i class="fas fa-edit mr-1"></i> Редактировать</button>
                                {% endif %}
                            {% elif item.is_unsupported_view %}
                                <button onclick="openUnsupportedViewModal('{{ item.path }}')" class="btn btn-info"><i class="fas fa-eye-slash mr-1"></i> Просмотреть (Неподдерживаемый)</button>
                                <a href="/download?path={{ item.path }}" class="btn btn-info"><i class="fas fa-download mr-1"></i> Скачать</a>
                            {% else %}
                                <button onclick="openViewModal('{{ item.path }}')" class="btn btn-info"><i class="fas fa-eye mr-1"></i> Просмотреть</button>
                            {% endif %}
                            <button onclick="showRenamePrompt('{{ item.path }}', '{{ item.name }}')" class="btn btn-info"><i class="fas fa-pen mr-1"></i> Переименовать</button>
                            <button onclick="showMoveCopyPrompt('{{ item.path }}', 'move')" class="btn btn-info"><i class="fas fa-arrows-alt mr-1"></i> Переместить</button>
                            <button onclick="showMoveCopyPrompt('{{ item.path }}', 'copy')" class="btn btn-info"><i class="fas fa-copy mr-1"></i> Копировать</button>
                            <button onclick="confirmAction('/delete?path={{ item.path }}&back={{ path }}', 'Вы уверены, что хотите удалить файл \\'{{ item.name }}\\'?')" class="btn btn-danger"><i class="fas fa-trash-alt mr-1"></i> Удалить</button>
                        </div>
                    {% endif %}
                </li>
            {% endfor %}
        </ul>
    </div>

    <div id="fileModal" class="modal">
        <div class="modal-content">
            <span class="close-button" onclick="closeModal()">&times;</span>
            <h2 id="modalTitle" class="text-xl font-bold mb-4"></h2>
            <textarea id="fileContent" class="mb-4" readonly></textarea>
            <div id="editButtons" class="flex justify-end space-x-2">
                <button id="saveButton" class="btn btn-success" onclick="saveFileContent()"><i class="fas fa-save mr-2"></i> Сохранить</button>
                <button id="cancelButton" class="btn btn-info" onclick="closeModal()"><i class="fas fa-times mr-2"></i> Отмена</button>
            </div>
        </div>
    </div>

    <div id="largeFileViewerModal" class="modal">
        <div class="modal-content max-w-3xl">
            <span class="close-button" onclick="closeLargeFileViewerModal()">&times;</span>
            <h2 id="largeFileViewerTitle" class="text-xl font-bold mb-4">Просмотр большого файла: <span id="largeFileName"></span></h2>
            <textarea id="largeFileContent" class="mb-4" readonly></textarea>
            <div class="flex justify-between items-center mb-4">
                <button id="prevChunkButton" class="btn btn-primary" onclick="loadChunk(-1)" disabled><i class="fas fa-chevron-left mr-2"></i> Предыдущий</button>
                <span id="chunkInfo" class="text-sm text-gray-600"></span>
                <button id="nextChunkButton" class="btn btn-primary" onclick="loadChunk(1)"><i class="fas fa-chevron-right ml-2"></i> Следующий</button>
            </div>
            <p class="text-red-600 text-sm">Примечание: Большие файлы доступны только для просмотра в браузере. Для редактирования скачайте файл.</p>
            <div class="flex justify-end space-x-2 mt-4">
                <a id="downloadLargeFileButton" href="#" class="btn btn-info"><i class="fas fa-download mr-2"></i> Скачать для Редактирования</a>
            </div>
        </div>
    </div>

    <div id="unsupportedFileModal" class="modal">
        <div class="modal-content max-w-sm">
            <span class="close-button" onclick="closeUnsupportedViewModal()">&times;</span>
            <h2 class="text-xl font-bold mb-4">Неподдерживаемый тип файла</h2>
            <p id="unsupportedFileMessage" class="mb-6 text-gray-700"></p>
            <div class="flex justify-end space-x-2">
                <a id="downloadUnsupportedFileButton" href="#" class="btn btn-info"><i class="fas fa-download mr-2"></i> Скачать</a>
                <button class="btn btn-info" onclick="closeUnsupportedViewModal()"><i class="fas fa-times mr-2"></i> Закрыть</button>
            </div>
        </div>
    </div>

    <div id="renameModal" class="modal">
        <div class="modal-content">
            <span class="close-button" onclick="closeRenameModal()">&times;</span>
            <h2 class="text-xl font-bold mb-4">Переименовать Элемент</h2>
            <form id="renameForm" action="/rename" method="post" class="flex flex-col space-y-3">
                <input type="hidden" name="old_path" id="renameOldPath">
                <input type="hidden" name="current_dir" value="{{ path }}">
                <label for="new_name" class="font-semibold">Новое Имя:</label>
                <input type="text" name="new_name" id="renameNewName" class="input-field" required>
                <button type="submit" class="btn btn-success"><i class="fas fa-check mr-2"></i> Переименовать</button>
            </form>
        </div>
    </div>

    <div id="moveCopyModal" class="modal">
        <div class="modal-content">
            <span class="close-button" onclick="closeMoveCopyModal()">&times;</span>
            <h2 id="moveCopyModalTitle" class="text-xl font-bold mb-4"></h2>
            <form id="moveCopyForm" method="post" class="flex flex-col space-y-3">
                <input type="hidden" name="source_path" id="moveCopySourcePath">
                <input type="hidden" name="operation_type" id="moveCopyOperationType">
                <input type="hidden" name="current_dir" value="{{ path }}">
                <label for="destination_path" class="font-semibold">Путь Назначения:</label>
                <input type="text" name="destination_path" id="moveCopyDestinationPath" class="input-field" placeholder="например, /путь/к/новой/локации" required>
                <button type="submit" class="btn btn-success" id="moveCopySubmitButton"><i class="fas fa-play mr-2"></i> Выполнить Действие</button>
            </form>
        </div>
    </div>

    <div id="confirmModal" class="modal">
        <div class="modal-content max-w-sm">
            <h2 id="confirmModalTitle" class="text-xl font-bold mb-4">Подтверждение</h2>
            <p id="confirmModalMessage" class="mb-6"></p>
            <div class="flex justify-end space-x-2">
                <button id="confirmYesButton" class="btn btn-danger"><i class="fas fa-check mr-2"></i> Да</button>
                <button id="confirmNoButton" class="btn btn-info"><i class="fas fa-times mr-2"></i> Отмена</button>
            </div>
        </div>
    </div>

    <div id="archiveModal" class="modal">
        <div class="modal-content max-w-2xl">
            <span class="close-button" onclick="closeArchiveModal()">&times;</span>
            <h2 id="archiveModalTitle" class="text-xl font-bold mb-4">Содержимое Архива: <span id="archiveFileName"></span></h2>
            <p id="archiveUnsupportedMessage" class="text-red-600 mb-4 hidden">Этот тип архива не поддерживается для просмотра содержимого или извлечения (поддерживаются ZIP, TAR, GZ).</p>
            <div id="archiveContentList" class="max-h-80 overflow-y-auto border border-gray-300 rounded-lg p-2 mb-4">
            </div>
            <div class="flex flex-col space-y-3 mb-4">
                <label for="extractDestination" class="font-semibold">Извлечь в (путь):</label>
                <input type="text" id="extractDestination" class="input-field" placeholder="Например, /home/user/extracted_files" value="{{ path }}">
            </div>
            <div class="flex justify-end space-x-2">
                <button id="extractSelectedButton" class="btn btn-primary" onclick="extractArchive(false)"><i class="fas fa-file-export mr-2"></i> Извлечь Выбранные</button>
                <button id="extractAllButton" class="btn btn-success" onclick="extractArchive(true)"><i class="fas fa-box-open mr-2"></i> Извлечь Все</button>
            </div>
        </div>
    </div>

    <div id="imagePreviewModal" class="modal">
        <div class="modal-content max-w-xl">
            <span class="close-button" onclick="closeImagePreviewModal()">&times;</span>
            <h2 id="imagePreviewTitle" class="text-xl font-bold mb-4">Предварительный просмотр изображения:</h2>
            <div class="flex justify-center items-center overflow-hidden max-h-[70vh]">
                <img id="imagePreview" src="" alt="Предварительный просмотр изображения" class="max-w-full max-h-full object-contain rounded-lg shadow-md">
            </div>
        </div>
    </div>

    <div id="messageBox" class="message-box"></div>

    <div id="loadingOverlay" class="loading-overlay">
        <div class="spinner"></div>
        <div id="loadingMessage">Загрузка...</div>
    </div>

    <script>
        let currentFilePath = '';
        let confirmCallback = null;
        let currentArchiveFilePath = '';

        let largeFileCurrentPath = '';
        let largeFileCurrentChunk = 1;
        let largeFileTotalLines = 0;
        const CHUNK_SIZE_LINES = {{ CHUNK_SIZE_LINES }};

        function showLoading(message = 'Выполнение операции...') {
            document.getElementById('loadingMessage').textContent = message;
            document.getElementById('loadingOverlay').style.display = 'flex';
        }

        function hideLoading() {
            document.getElementById('loadingOverlay').style.display = 'none';
        }

        function showMessage(message, isError = false) {
            const msgBox = document.getElementById('messageBox');
            msgBox.textContent = message;
            msgBox.classList.remove('error');
            if (isError) {
                msgBox.classList.add('error');
            }
            msgBox.style.display = 'block';
            msgBox.style.animation = 'none';
            void msgBox.offsetWidth;
            msgBox.style.animation = null;
        }

        function confirmAction(url, message) {
            document.getElementById('confirmModalTitle').textContent = 'Подтверждение Действия';
            document.getElementById('confirmModalMessage').textContent = message;
            document.getElementById('confirmModal').style.display = 'flex';

            confirmCallback = function(result) {
                document.getElementById('confirmModal').style.display = 'none';
                if (result) {
                    showLoading('Выполнение...');
                    window.location.href = url;
                }
            };
        }

        document.getElementById('confirmYesButton').onclick = function() {
            if (confirmCallback) confirmCallback(true);
        };
        document.getElementById('confirmNoButton').onclick = function() {
            if (confirmCallback) confirmCallback(false);
        };

        async function openEditModal(filePath) {
            currentFilePath = filePath;
            document.getElementById('modalTitle').textContent = `Редактирование: ${filePath.split('/').pop()}`;
            document.getElementById('fileContent').readOnly = false;
            document.getElementById('saveButton').style.display = 'inline-flex';

            showLoading('Загрузка файла...');
            try {
                const response = await fetch(`/get_file_content?path=${encodeURIComponent(filePath)}`);
                if (!response.ok) {
                    throw new Error(`Ошибка HTTP! статус: ${response.status}`);
                }
                const data = await response.json();
                if (data.error) {
                    document.getElementById('fileContent').value = `Ошибка загрузки файла: ${data.error}`;
                    showMessage(`Ошибка загрузки файла: ${data.error}`, true);
                } else {
                    document.getElementById('fileContent').value = data.content;
                }
            } catch (error) {
                console.error('Ошибка получения содержимого файла:', error);
                document.getElementById('fileContent').value = `Не удалось загрузить содержимое файла: ${error.message}`;
                showMessage(`Не удалось загрузить содержимое файла: ${error.message}`, true);
            } finally {
                hideLoading();
            }
            document.getElementById('fileModal').style.display = 'flex';
        }

        async function openViewModal(filePath) {
            currentFilePath = filePath;
            document.getElementById('modalTitle').textContent = `Просмотр: ${filePath.split('/').pop()}`;
            document.getElementById('fileContent').readOnly = true;
            document.getElementById('saveButton').style.display = 'none';

            showLoading('Загрузка файла...');
            try {
                const response = await fetch(`/get_file_content?path=${encodeURIComponent(filePath)}`);
                if (!response.ok) {
                    throw new Error(`Ошибка HTTP! статус: ${response.status}`);
                }
                const data = await response.json();
                if (data.error) {
                    document.getElementById('fileContent').value = `Ошибка загрузки файла: ${data.error}`;
                    showMessage(`Ошибка загрузки файла: ${data.error}`, true);
                } else {
                    document.getElementById('fileContent').value = data.content;
                }
            } catch (error) {
                console.error('Ошибка получения содержимого файла:', error);
                document.getElementById('fileContent').value = `Не удалось загрузить содержимое файла: ${error.message}`;
                showMessage(`Не удалось загрузить содержимое файла: ${error.message}`, true);
            } finally {
                hideLoading();
            }
            document.getElementById('fileModal').style.display = 'flex';
        }

        async function saveFileContent() {
            const content = document.getElementById('fileContent').value;
            showLoading('Сохранение файла...');
            try {
                const response = await fetch('/save_file_content', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ path: currentFilePath, content: content }),
                });
                const result = await response.json();
                if (result.success) {
                    showMessage('Файл успешно сохранен!');
                    closeModal();
                } else {
                    showMessage(`Ошибка сохранения файла: ${result.error}`, true);
                }
            } catch (error) {
                console.error('Ошибка сохранения содержимого файла:', error);
                showMessage(`Не удалось сохранить файл: ${error.message}`, true);
            } finally {
                hideLoading();
            }
        }

        function closeModal() {
            document.getElementById('fileModal').style.display = 'none';
            document.getElementById('fileContent').value = '';
            currentFilePath = '';
        }

        async function openLargeFileViewerModal(filePath, initialChunk = 1) {
            largeFileCurrentPath = filePath;
            largeFileCurrentChunk = initialChunk;
            document.getElementById('largeFileName').textContent = filePath.split('/').pop();
            document.getElementById('downloadLargeFileButton').href = `/download?path=${encodeURIComponent(filePath)}`;

            await fetchLargeFileChunk();
            document.getElementById('largeFileViewerModal').style.display = 'flex';
        }

        async function fetchLargeFileChunk() {
            showLoading('Загрузка части файла...');
            try {
                const response = await fetch(`/get_file_chunk_content?path=${encodeURIComponent(largeFileCurrentPath)}&chunk_number=${largeFileCurrentChunk}&chunk_size=${CHUNK_SIZE_LINES}`);
                if (!response.ok) {
                    throw new Error(`Ошибка HTTP! статус: ${response.status}`);
                }
                const data = await response.json();

                if (data.error) {
                    document.getElementById('largeFileContent').value = `Ошибка загрузки части файла: ${data.error}`;
                    showMessage(`Ошибка загрузки части файла: ${data.error}`, true);
                } else {
                    document.getElementById('largeFileContent').value = data.content;
                    largeFileTotalLines = data.total_lines;
                    updateChunkInfo(data.current_start_line, data.current_end_line, data.total_lines);
                    updateChunkButtons();
                }
            } catch (error) {
                console.error('Ошибка получения части файла:', error);
                document.getElementById('largeFileContent').value = `Не удалось загрузить часть файла: ${error.message}`;
                showMessage(`Не удалось загрузить часть файла: ${error.message}`, true);
            } finally {
                hideLoading();
            }
        }

        function updateChunkInfo(start, end, total) {
            document.getElementById('chunkInfo').textContent = `Строки ${start}-${end} из ${total}`;
        }

        function updateChunkButtons() {
            const prevButton = document.getElementById('prevChunkButton');
            const nextButton = document.getElementById('nextChunkButton');
            const totalChunks = Math.ceil(largeFileTotalLines / CHUNK_SIZE_LINES);

            prevButton.disabled = largeFileCurrentChunk <= 1;
            nextButton.disabled = largeFileCurrentChunk >= totalChunks;
        }

        function loadChunk(direction) {
            largeFileCurrentChunk += direction;
            fetchLargeFileChunk();
        }

        function closeLargeFileViewerModal() {
            document.getElementById('largeFileViewerModal').style.display = 'none';
            document.getElementById('largeFileContent').value = '';
            largeFileCurrentPath = '';
            largeFileCurrentChunk = 1;
            largeFileTotalLines = 0;
        }

        function openUnsupportedViewModal(filePath) {
            const fileName = filePath.split('/').pop();
            let message = '';
            if (fileName.toLowerCase().endsWith('.db')) {
                message = `Файлы баз данных (.db) не могут быть просмотрены или отредактированы напрямую в браузере. Пожалуйста, скачайте файл для работы с ним локально.`;
            } else if (fileName.toLowerCase().endsWith('.xlsx')) {
                message = `Файлы Excel (.xlsx) не могут быть просмотрены или отредактированы напрямую в браузере. Пожалуйста, скачайте файл для работы с ним локально.`;
            } else {
                message = `Этот тип файла (${fileName.split('.').pop()}) не поддерживается для просмотра или редактирования в браузере.`;
            }
            document.getElementById('unsupportedFileMessage').textContent = message;
            document.getElementById('downloadUnsupportedFileButton').href = `/download?path=${encodeURIComponent(filePath)}`;
            document.getElementById('unsupportedFileModal').style.display = 'flex';
        }

        function closeUnsupportedViewModal() {
            document.getElementById('unsupportedFileModal').style.display = 'none';
            document.getElementById('unsupportedFileMessage').textContent = '';
            document.getElementById('downloadUnsupportedFileButton').href = '#';
        }


        function showRenamePrompt(oldPath, oldName) {
            document.getElementById('renameOldPath').value = oldPath;
            document.getElementById('renameNewName').value = oldName;
            document.getElementById('renameModal').style.display = 'flex';
        }

        function closeRenameModal() {
            document.getElementById('renameModal').style.display = 'none';
            document.getElementById('renameOldPath').value = '';
            document.getElementById('renameNewName').value = '';
        }

        function showMoveCopyPrompt(sourcePath, operationType) {
            document.getElementById('moveCopySourcePath').value = sourcePath;
            document.getElementById('moveCopyOperationType').value = operationType;
            document.getElementById('moveCopyModalTitle').textContent = `${operationType === 'move' ? 'Переместить' : 'Копировать'} Элемент: ${sourcePath.split('/').pop()}`;
            document.getElementById('moveCopySubmitButton').innerHTML = `<i class="fas fa-${operationType === 'move' ? 'arrows-alt' : 'copy'} mr-2"></i> ${operationType === 'move' ? 'Переместить' : 'Копировать'}`;
            
            document.getElementById('moveCopyDestinationPath').value = document.querySelector('input[name="path"]').value;

            document.getElementById('moveCopyModal').style.display = 'flex';
        }

        function closeMoveCopyModal() {
            document.getElementById('moveCopyModal').style.display = 'none';
            document.getElementById('moveCopySourcePath').value = '';
            document.getElementById('moveCopyOperationType').value = '';
            document.getElementById('moveCopyDestinationPath').value = '';
        }

        document.getElementById('moveCopyForm').addEventListener('submit', async function(event) {
            event.preventDefault();
            const sourcePath = document.getElementById('moveCopySourcePath').value;
            const operationType = document.getElementById('moveCopyOperationType').value;
            const destinationPath = document.getElementById('moveCopyDestinationPath').value;
            const currentDir = document.querySelector('input[name="current_dir"]').value;

            showLoading(`${operationType === 'move' ? 'Перемещение' : 'Копирование'}...`);
            try {
                const response = await fetch(`/${operationType}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ source_path: sourcePath, destination_path: destinationPath }),
                });
                const result = await response.json();
                if (result.success) {
                    showMessage(`${operationType === 'move' ? 'Перемещение' : 'Копирование'} успешно!`);
                    closeMoveCopyModal();
                    window.location.href = `/?path=${encodeURIComponent(currentDir)}`;
                } else {
                    showMessage(`Ошибка во время ${operationType === 'move' ? 'перемещения' : 'копирования'}: ${result.error}`, true);
                }
            } catch (error) {
                console.error(`Ошибка во время ${operationType === 'move' ? 'перемещения' : 'копирования'}:`, error);
                showMessage(`Не удалось выполнить ${operationType === 'move' ? 'перемещение' : 'копирование'}: ${error.message}`, true);
            } finally {
                hideLoading();
            }
        });

        window.onclick = function(event) {
            if (event.target == document.getElementById('fileModal')) {
                closeModal();
            }
            if (event.target == document.getElementById('renameModal')) {
                closeRenameModal();
            }
            if (event.target == document.getElementById('moveCopyModal')) {
                closeMoveCopyModal();
            }
            if (event.target == document.getElementById('confirmModal')) {
                if (confirmCallback) confirmCallback(false);
            }
            if (event.target == document.getElementById('archiveModal')) {
                closeArchiveModal();
            }
            if (event.target == document.getElementById('imagePreviewModal')) {
                closeImagePreviewModal();
            }
            if (event.target == document.getElementById('largeFileViewerModal')) {
                closeLargeFileViewerModal();
            }
            if (event.target == document.getElementById('unsupportedFileModal')) {
                closeUnsupportedViewModal();
            }
        }

        function filterList() {
            const input = document.getElementById('searchInput');
            const filter = input.value.toLowerCase();
            const ul = document.getElementById('fileList');
            const li = ul.getElementsByTagName('li');

            for (let i = 0; i < li.length; i++) {
                const name = li[i].getAttribute('data-name');
                if (name) {
                    if (name.includes(filter)) {
                        li[i].style.display = '';
                    } else {
                        li[i].style.display = 'none';
                    }
                } else {
                    if ("..".includes(filter)) {
                        li[i].style.display = '';
                    } else {
                        li[i].style.display = 'none';
                    }
                }
            }
        }

        async function openArchiveModal(archivePath) {
            currentArchiveFilePath = archivePath;
            const fileName = archivePath.split('/').pop();
            document.getElementById('archiveFileName').textContent = fileName;
            const archiveContentList = document.getElementById('archiveContentList');
            archiveContentList.innerHTML = '';
            document.getElementById('archiveUnsupportedMessage').classList.add('hidden');

            showLoading('Загрузка содержимого архива...');
            try {
                const response = await fetch(`/view_archive?path=${encodeURIComponent(archivePath)}`);
                if (!response.ok) {
                    throw new Error(`Ошибка HTTP! статус: ${response.status}`);
                }
                const data = await response.json();

                if (data.error) {
                    archiveContentList.innerHTML = `<p class="text-red-600">${data.error}</p>`;
                    if (data.error.includes("неподдерживаемый формат")) {
                        document.getElementById('archiveUnsupportedMessage').classList.remove('hidden');
                    }
                    showMessage(`Ошибка при просмотре архива: ${data.error}`, true);
                } else {
                    if (data.contents && data.contents.length > 0) {
                        data.contents.forEach(item => {
                            const div = document.createElement('div');
                            div.className = 'flex items-center py-1';
                            const checkbox = document.createElement('input');
                            checkbox.type = 'checkbox';
                            checkbox.value = item;
                            checkbox.className = 'mr-2';
                            div.appendChild(checkbox);
                            const icon = document.createElement('i');
                            icon.className = `mr-2 ${item.endsWith('/') ? 'fas fa-folder text-yellow-500' : 'fas fa-file text-blue-500'}`;
                            div.appendChild(icon);
                            const span = document.createElement('span');
                            span.textContent = item;
                            div.appendChild(span);
                            archiveContentList.appendChild(div);
                        });
                    } else {
                        archiveContentList.innerHTML = '<p class="text-gray-500">Архив пуст или не содержит файлов.</p>';
                    }
                }
            } catch (error) {
                console.error('Ошибка при просмотре архива:', error);
                archiveContentList.innerHTML = `<p class="text-red-600">Не удалось загрузить содержимое архива: ${error.message}</p>`;
                showMessage(`Не удалось загрузить содержимое архива: ${error.message}`, true);
            } finally {
                hideLoading();
            }
            document.getElementById('archiveModal').style.display = 'flex';
        }

        function closeArchiveModal() {
            document.getElementById('archiveModal').style.display = 'none';
            document.getElementById('archiveContentList').innerHTML = '';
            document.getElementById('extractDestination').value = document.querySelector('input[name="path"]').value;
            currentArchiveFilePath = '';
        }

        async function extractArchive(extractAll) {
            const destinationPath = document.getElementById('extractDestination').value;
            if (!destinationPath) {
                showMessage('Пожалуйста, укажите путь назначения для извлечения.', true);
                return;
            }

            let itemsToExtract = [];
            if (!extractAll) {
                document.querySelectorAll('#archiveContentList input[type="checkbox"]:checked').forEach(checkbox => {
                    itemsToExtract.push(checkbox.value);
                });
                if (itemsToExtract.length === 0) {
                    showMessage('Пожалуйста, выберите элементы для извлечения или используйте "Извлечь Все".', true);
                    return;
                }
            } else {
                itemsToExtract = ['_ALL_'];
            }

            showLoading('Извлечение архива...');
            try {
                const response = await fetch('/extract_archive', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        archive_path: currentArchiveFilePath,
                        items_to_extract: itemsToExtract,
                        destination_path: destinationPath
                    }),
                });
                const result = await response.json();
                if (result.success) {
                    showMessage('Архив успешно извлечен!');
                    closeArchiveModal();
                    const currentDir = document.querySelector('input[name="path"]').value;
                    if (destinationPath.startsWith(currentDir) || currentDir.startsWith(destinationPath)) {
                        window.location.href = `/?path=${encodeURIComponent(destinationPath)}`;
                    } else {
                        window.location.reload();
                    }
                } else {
                    showMessage(`Ошибка извлечения архива: ${result.error}`, true);
                }
            } catch (error) {
                console.error('Ошибка извлечения архива:', error);
                showMessage(`Не удалось извлечь архив: ${error.message}`, true);
            } finally {
                hideLoading();
            }
        }

        function openImagePreviewModal(imagePath) {
            document.getElementById('imagePreviewTitle').textContent = `Предварительный просмотр: ${imagePath.split('/').pop()}`;
            document.getElementById('imagePreview').src = `/view_image?path=${encodeURIComponent(imagePath)}`;
            document.getElementById('imagePreviewModal').style.display = 'flex';
        }

        function closeImagePreviewModal() {
            document.getElementById('imagePreviewModal').style.display = 'none';
            document.getElementById('imagePreview').src = '';
        }

        const dropZone = document.getElementById('dropZone');
        const uploadForm = document.getElementById('uploadForm');
        const currentPathInput = uploadForm.querySelector('input[name="path"]');

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('highlight');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('highlight');
        });

        dropZone.addEventListener('drop', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('highlight');

            const files = e.dataTransfer.files;
            if (files.length === 0) {
                return;
            }

            showLoading('Загрузка файлов...');
            const formData = new FormData();
            formData.append('path', currentPathInput.value);
            
            for (let i = 0; i < files.length; i++) {
                formData.append('file', files[i]);
            }

            try {
                const response = await fetch('/upload_multiple', {
                    method: 'POST',
                    body: formData,
                });
                const result = await response.json();
                if (result.success) {
                    showMessage(`Успешно загружено ${result.uploaded_count} файл(ов)!`);
                    window.location.reload();
                } else {
                    showMessage(`Ошибка загрузки: ${result.error}`, true);
                }
            } catch (error) {
                console.error('Ошибка загрузки файлов:', error);
                showMessage(`Не удалось загрузить файлы: ${error.message}`, true);
            } finally {
                hideLoading();
            }
        });

        uploadForm.addEventListener('submit', () => {
            showLoading('Загрузка файла...');
        });

    </script>
</body>
</html>
'''

def is_text_file(filepath):
    text_extensions = ['.txt', '.log', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv', '.yml', '.yaml', '.conf', '.ini', '.sh', '.bash', '.zsh', '.c', '.cpp', '.h', '.hpp', '.java', '.go', '.php', '.rb', '.swift', '.kt', '.ts', '.jsx', '.tsx', '.vue', '.toml', '.rtf', '.nfo', '.sql']
    _, ext = os.path.splitext(filepath)
    return ext.lower() in text_extensions

def is_archive_file(filepath):
    archive_extensions = ['.zip', '.tar', '.gz', '.tgz', '.rar']
    _, ext = os.path.splitext(filepath)
    return ext.lower() in archive_extensions

def is_image_file(filepath):
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico']
    _, ext = os.path.splitext(filepath)
    return ext.lower() in image_extensions

def is_xlsx_file(filepath):
    _, ext = os.path.splitext(filepath)
    return ext.lower() == '.xlsx'

def is_db_file(filepath):
    _, ext = os.path.splitext(filepath)
    return ext.lower() == '.db'

def get_human_readable_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

@app.route('/')
def index():
    path = request.args.get('path', BASE_DIR)
    path = os.path.abspath(path)

    if not path.startswith(BASE_DIR):
        path = BASE_DIR

    if not os.path.exists(path):
        return f"❌ Путь не существует: {path}", 404
    if not os.path.isdir(path):
        return redirect(url_for('index', path=os.path.dirname(path)))

    try:
        items = []
        for name in os.listdir(path):
            full_path = os.path.join(path, name)
            try:
                if os.path.islink(full_path):
                    continue
                
                is_dir = os.path.isdir(full_path)
                item_size = ""
                is_text = False
                is_archive = False
                is_image = False
                is_large_text = False
                is_unsupported_view = False
                permissions = ""

                try:
                    mode = os.stat(full_path).st_mode
                    permissions = stat.filemode(mode)
                except OSError:
                    permissions = "N/A"

                if not is_dir:
                    file_size = os.path.getsize(full_path)
                    item_size = get_human_readable_size(file_size)
                    is_text = is_text_file(full_path)
                    is_archive = is_archive_file(full_path)
                    is_image = is_image_file(full_path)
                    
                    if is_text and file_size > LARGE_FILE_THRESHOLD_BYTES:
                        is_large_text = True
                    
                    if is_db_file(full_path) or is_xlsx_file(full_path):
                        is_unsupported_view = True


                items.append({
                    'name': name,
                    'path': full_path,
                    'isdir': is_dir,
                    'size': item_size,
                    'is_text': is_text,
                    'is_archive': is_archive,
                    'is_image': is_image,
                    'is_large_text': is_large_text,
                    'is_unsupported_view': is_unsupported_view,
                    'permissions': permissions
                })
            except OSError as e:
                print(f"Предупреждение: Не удалось получить доступ к {full_path} - {e}")
                items.append({
                    'name': f"{name} (Доступ Запрещен)",
                    'path': full_path,
                    'isdir': os.path.isdir(full_path),
                    'size': '',
                    'is_text': False,
                    'is_archive': False,
                    'is_image': False,
                    'is_large_text': False,
                    'is_unsupported_view': False,
                    'permissions': '---------',
                    'error': True
                })
        
        items.sort(key=lambda x: (not x['isdir'], not x['is_archive'], not x['is_image'], not x['is_text'], x['name'].lower()))

        parent = os.path.dirname(path)
        if not parent.startswith(BASE_DIR) and parent != '/':
            parent = BASE_DIR
        if parent == path:
            parent = None

        return render_template_string(HTML_TEMPLATE, path=path, items=items, parent=parent, CHUNK_SIZE_LINES=CHUNK_SIZE_LINES)
    except Exception as e:
        return f"❌ Ошибка: {e}", 500

@app.route('/download')
def download():
    path = request.args.get('path')
    if not path or not os.path.isfile(path):
        return "❌ Недействительный путь к файлу", 400
    if not os.path.abspath(path).startswith(BASE_DIR):
        return "❌ Доступ запрещен: Невозможно скачать файлы за пределами базовой директории.", 403
    try:
        return send_file(path, as_attachment=True)
    except Exception as e:
        return f"❌ Ошибка загрузки файла: {e}", 500

@app.route('/delete')
def delete():
    path = request.args.get('path')
    back = request.args.get('back', BASE_DIR)
    if not path:
        return "❌ Не указан путь для удаления", 400
    if not os.path.abspath(path).startswith(BASE_DIR):
        return "❌ Доступ запрещен: Невозможно удалить файлы/папки за пределами базовой директории.", 403

    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        return redirect(url_for('index', path=back))
    except Exception as e:
        return f"❌ Ошибка удаления {os.path.basename(path)}: {e}", 500

@app.route('/upload', methods=['POST'])
def upload():
    path = request.form['path']
    file = request.files['file']
    if not path:
        return "❌ Не указан путь для загрузки", 400
    if not os.path.abspath(path).startswith(BASE_DIR):
        return "❌ Доступ запрещен: Невозможно загрузить файлы за пределами базовой директории.", 403

    if file:
        try:
            file.save(os.path.join(path, file.filename))
            return redirect(url_for('index', path=path))
        except Exception as e:
            return f"❌ Ошибка загрузки файла: {e}", 500
    return "❌ Файл для загрузки не выбран", 400

@app.route('/upload_multiple', methods=['POST'])
def upload_multiple():
    path = request.form['path']
    if not path:
        return jsonify(success=False, error="Не указан путь для загрузки."), 400
    if not os.path.abspath(path).startswith(BASE_DIR):
        return jsonify(success=False, error="Доступ запрещен: Невозможно загрузить файлы за пределами базовой директории."), 403

    uploaded_count = 0
    errors = []
    for key, file in request.files.items():
        if file:
            try:
                file.save(os.path.join(path, file.filename))
                uploaded_count += 1
            except Exception as e:
                errors.append(f"Ошибка загрузки файла {file.filename}: {e}")
    
    if errors:
        return jsonify(success=False, error="\n".join(errors)), 500
    return jsonify(success=True, uploaded_count=uploaded_count)


@app.route('/create_folder', methods=['POST'])
def create_folder():
    current_path = request.form['current_path']
    folder_name = request.form['folder_name']
    new_folder_path = os.path.join(current_path, folder_name)

    if not os.path.abspath(current_path).startswith(BASE_DIR):
        return "❌ Доступ запрещен: Невозможно создать папку за пределами базовой директории.", 403

    try:
        os.makedirs(new_folder_path, exist_ok=True)
        return redirect(url_for('index', path=current_path))
    except Exception as e:
        return f"❌ Ошибка создания папки: {e}", 500

@app.route('/create_file', methods=['POST'])
def create_file():
    current_path = request.form['current_path']
    file_name = request.form['file_name']
    new_file_path = os.path.join(current_path, file_name)

    if not os.path.abspath(current_path).startswith(BASE_DIR):
        return "❌ Доступ запрещен: Невозможно создать файл за пределами базовой директории.", 403

    try:
        with open(new_file_path, 'w') as f:
            f.write("")
        return redirect(url_for('index', path=current_path))
    except Exception as e:
        return f"❌ Ошибка создания файла: {e}", 500

@app.route('/rename', methods=['POST'])
def rename():
    old_path = request.form['old_path']
    new_name = request.form['new_name']
    current_dir = request.form['current_dir']

    if not os.path.abspath(old_path).startswith(BASE_DIR):
        return jsonify(success=False, error="Доступ запрещен: Невозможно переименовать элементы за пределами базовой директории."), 403
    
    new_path = os.path.join(os.path.dirname(old_path), new_name)
    if not os.path.abspath(new_path).startswith(BASE_DIR):
        return jsonify(success=False, error="Доступ запрещен: Невозможно переименовать в путь за пределами базовой директории."), 403

    try:
        os.rename(old_path, new_path)
        return redirect(url_for('index', path=current_dir))
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/get_file_content')
def get_file_content():
    path = request.args.get('path')
    if not path or not os.path.isfile(path):
        return jsonify(error="Недействительный путь к файлу."), 400
    if not os.path.abspath(path).startswith(BASE_DIR):
        return jsonify(error="Доступ запрещен: Невозможно просмотреть файлы за пределами базовой директории."), 403

    try:
        file_size = os.path.getsize(path)
        if file_size > LARGE_FILE_THRESHOLD_BYTES:
            return jsonify(error="Файл слишком большой для прямого редактирования. Используйте просмотр больших файлов."), 413

        if is_db_file(path) or is_xlsx_file(path):
            return jsonify(error="Прямое редактирование этого типа файла в браузере не поддерживается. Вы можете скачать файл для работы с ним локально."), 400

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return jsonify(content=content)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/get_file_chunk_content')
def get_file_chunk_content():
    path = request.args.get('path')
    chunk_number = int(request.args.get('chunk_number', 1))
    chunk_size = int(request.args.get('chunk_size', CHUNK_SIZE_LINES))

    if not path or not os.path.isfile(path):
        return jsonify(error="Недействительный путь к файлу."), 400
    if not os.path.abspath(path).startswith(BASE_DIR):
        return jsonify(error="Доступ запрещен: Невозможно просмотреть файлы за пределами базовой директории."), 403

    try:
        total_lines = 0
        lines = []
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                total_lines += 1
        
        start_line_index = (chunk_number - 1) * chunk_size
        end_line_index = start_line_index + chunk_size
        
        current_line_count = 0
        current_chunk_content = []

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= start_line_index and i < end_line_index:
                    current_chunk_content.append(line)
                if i >= end_line_index:
                    break
        
        return jsonify(
            content="".join(current_chunk_content),
            total_lines=total_lines,
            current_start_line=start_line_index + 1,
            current_end_line=min(end_line_index, total_lines)
        )
    except Exception as e:
        print(f"Error reading file chunk {path}: {e}")
        return jsonify(error=str(e)), 500


@app.route('/save_file_content', methods=['POST'])
def save_file_content():
    data = request.get_json()
    path = data.get('path')
    content = data.get('content')

    if not path or content is None:
        return jsonify(success=False, error="Неверные данные запроса."), 400
    if not os.path.isfile(path):
        return jsonify(success=False, error="Файл не существует или не является файлом."), 404
    if not os.path.abspath(path).startswith(BASE_DIR):
        return jsonify(success=False, error="Доступ запрещен: Невозможно сохранить файлы за пределами базовой директории."), 403

    if os.path.getsize(path) > LARGE_FILE_THRESHOLD_BYTES:
        return jsonify(success=False, error="Файл слишком большой для прямого редактирования. Скачайте его для изменения."), 400

    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/move', methods=['POST'])
def move_item():
    data = request.get_json()
    source_path = data.get('source_path')
    destination_path = data.get('destination_path')

    if not source_path or not destination_path:
        return jsonify(success=False, error="Отсутствует исходный или целевой путь."), 400

    if not os.path.abspath(source_path).startswith(BASE_DIR):
        return jsonify(success=False, error="Доступ запрещен: Невозможно перемещать из-за пределов базовой директории."), 403
    if not os.path.abspath(destination_path).startswith(BASE_DIR):
        return jsonify(success=False, error="Доступ запрещен: Невозможно перемещать за пределы базовой директории."), 403

    try:
        if os.path.isdir(destination_path):
            shutil.move(source_path, os.path.join(destination_path, os.path.basename(source_path)))
        else:
            shutil.move(source_path, destination_path)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/copy', methods=['POST'])
def copy_item():
    data = request.get_json()
    source_path = data.get('source_path')
    destination_path = data.get('destination_path')

    if not source_path or not destination_path:
        return jsonify(success=False, error="Отсутствует исходный или целевой путь."), 400

    if not os.path.abspath(source_path).startswith(BASE_DIR):
        return jsonify(success=False, error="Доступ запрещен: Невозможно копировать из-за пределов базовой директории."), 403
    if not os.path.abspath(destination_path).startswith(BASE_DIR):
        return jsonify(success=False, error="Доступ запрещен: Невозможно копировать за пределы базовой директории."), 403

    try:
        if os.path.isdir(destination_path):
            if os.path.isfile(source_path):
                shutil.copy(source_path, os.path.join(destination_path, os.path.basename(source_path)))
            elif os.path.isdir(source_path):
                dest_dir = os.path.join(destination_path, os.path.basename(source_path))
                shutil.copytree(source_path, dest_dir)
        else:
            if os.path.isfile(source_path):
                shutil.copy(source_path, destination_path)
            elif os.path.isdir(source_path):
                shutil.copytree(source_path, destination_path)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@app.route('/view_archive')
def view_archive():
    archive_path = request.args.get('path')
    if not archive_path or not os.path.isfile(archive_path):
        return jsonify(error="Недействительный путь к архиву."), 400
    if not os.path.abspath(archive_path).startswith(BASE_DIR):
        return jsonify(error="Доступ запрещен: Невозможно просмотреть архивы за пределами базовой директории."), 403

    contents = []
    try:
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, 'r') as zf:
                contents = [info.filename for info in zf.infolist()]
        elif tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, 'r') as tf:
                contents = [member.name for member in tf.getmembers()]
        elif archive_path.lower().endswith('.gz') or archive_path.lower().endswith('.tgz'):
            if tarfile.is_tarfile(archive_path):
                with tarfile.open(archive_path, 'r:gz') as tf:
                    contents = [member.name for member in tf.getmembers()]
            else:
                base_name = os.path.basename(archive_path)
                if base_name.lower().endswith('.gz'):
                    base_name = base_name[:-3]
                contents = [base_name + " (GZ архив)"]
        elif archive_path.lower().endswith('.rar'):
            return jsonify(error="Формат RAR не поддерживается для просмотра содержимого или извлечения из-за отсутствия встроенной поддержки Python. Пожалуйста, используйте ZIP, TAR или GZ."), 400
        else:
            return jsonify(error="Неподдерживаемый формат архива."), 400

        return jsonify(contents=contents)
    except Exception as e:
        print(f"Server error viewing archive {archive_path}: {e}")
        return jsonify(error=f"Ошибка при чтении архива: {e}"), 500

@app.route('/extract_archive', methods=['POST'])
def extract_archive():
    data = request.get_json()
    archive_path = data.get('archive_path')
    items_to_extract = data.get('items_to_extract')
    destination_path = data.get('destination_path')

    if not archive_path or not destination_path:
        return jsonify(success=False, error="Отсутствует путь к архиву или путь назначения."), 400
    if not os.path.isfile(archive_path):
        return jsonify(success=False, error="Архив не существует."), 404
    
    if not os.path.isdir(destination_path):
        try:
            os.makedirs(destination_path, exist_ok=True)
        except OSError as e:
            if e.errno == 13:
                return jsonify(success=False, error=f"Ошибка разрешений: Невозможно создать директорию назначения '{destination_path}'. Проверьте права доступа."), 403
            return jsonify(success=False, error=f"Не удалось создать директорию назначения '{destination_path}': {e}"), 500

    if not os.path.abspath(archive_path).startswith(BASE_DIR):
        return jsonify(success=False, error="Доступ запрещен: Невозможно извлечь из архива за пределами базовой директории."), 403
    if not os.path.abspath(destination_path).startswith(BASE_DIR):
        return jsonify(success=False, error="Доступ запрещен: Невозможно извлечь в директорию за пределами базовой директории."), 403

    try:
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, 'r') as zf:
                if '_ALL_' in items_to_extract:
                    zf.extractall(destination_path)
                else:
                    for item in items_to_extract:
                        extracted_item_path = os.path.abspath(os.path.join(destination_path, item))
                        if not extracted_item_path.startswith(os.path.abspath(destination_path)):
                            print(f"Skipping potentially malicious path in zip: {item}")
                            continue
                        zf.extract(item, destination_path)
        elif tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, 'r') as tf:
                members = tf.getmembers()
                safe_members = []
                for member in members:
                    extracted_path = os.path.abspath(os.path.join(destination_path, member.name))
                    if not extracted_path.startswith(os.path.abspath(destination_path)):
                        print(f"Skipping potentially malicious path in tar: {member.name}")
                        continue
                    if '_ALL_' in items_to_extract or member.name in items_to_extract:
                        safe_members.append(member)
                
                tf.extractall(destination_path, members=safe_members)
        elif archive_path.lower().endswith('.gz') or archive_path.lower().endswith('.tgz'):
            if tarfile.is_tarfile(archive_path):
                with tarfile.open(archive_path, 'r:gz') as tf:
                    members = tf.getmembers()
                    safe_members = []
                    for member in members:
                        extracted_path = os.path.abspath(os.path.join(destination_path, member.name))
                        if not extracted_path.startswith(os.path.abspath(destination_path)):
                            print(f"Skipping potentially malicious path in tar.gz: {member.name}")
                            continue
                        if '_ALL_' in items_to_extract or member.name in items_to_extract:
                            safe_members.append(member)
                    tf.extractall(destination_path, members=safe_members)
            elif archive_path.lower().endswith('.gz'):
                if '_ALL_' in items_to_extract or os.path.basename(archive_path) + " (GZ архив)" in items_to_extract:
                    with gzip.open(archive_path, 'rb') as f_in:
                        output_filename = os.path.basename(archive_path)
                        if output_filename.endswith('.gz'):
                            output_filename = output_filename[:-3]
                        output_path = os.path.join(destination_path, output_filename)
                        
                        if not os.path.abspath(output_path).startswith(os.path.abspath(destination_path)):
                            return jsonify(success=False, error="Попытка извлечения вне целевой директории."), 403

                        with open(output_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                else:
                    return jsonify(success=False, error="Для GZ архивов можно извлечь только весь файл.")
        else:
            return jsonify(success=False, error="Неподдерживаемый формат архива для извлечения.")

        return jsonify(success=True)
    except Exception as e:
        print(f"Server error extracting archive {archive_path}: {e}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/view_image')
def view_image():
    image_path = request.args.get('path')
    if not image_path or not os.path.isfile(image_path):
        return "❌ Недействительный путь к изображению", 400
    if not os.path.abspath(image_path).startswith(BASE_DIR):
        return "❌ Доступ запрещен: Невозможно просмотреть изображения за пределами базовой директории.", 403
    
    try:
        mimetype, _ = mimetypes.guess_type(image_path)
        if not mimetype or not mimetype.startswith('image/'):
            return "❌ Не является файлом изображения", 400
        
        return send_file(image_path, mimetype=mimetype)
    except Exception as e:
        return f"❌ Ошибка при просмотре изображения: {e}", 500


if __name__ == '__main__':
    os.makedirs(BASE_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=8080, debug=True)


