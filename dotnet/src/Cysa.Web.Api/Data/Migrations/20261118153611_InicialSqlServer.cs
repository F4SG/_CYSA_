using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Cysa.Web.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class InicialSqlServer : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "Corredor",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    Nombre = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Descripcion = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Corredor", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "Decisiones",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    SolicitudId = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    PlanId = table.Column<string>(type: "nvarchar(64)", maxLength: 64, nullable: false),
                    Version = table.Column<int>(type: "int", nullable: false),
                    UsuarioId = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    SolicitudJson = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    ResultadoJson = table.Column<string>(type: "nvarchar(max)", nullable: false),
                    EvaluacionJson = table.Column<string>(type: "nvarchar(max)", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Decisiones", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "Evaluaciones",
                columns: table => new
                {
                    Id = table.Column<Guid>(type: "uniqueidentifier", nullable: false),
                    PlanId = table.Column<string>(type: "nvarchar(64)", maxLength: 64, nullable: false),
                    Version = table.Column<int>(type: "int", nullable: false),
                    Json = table.Column<string>(type: "nvarchar(max)", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Evaluaciones", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "Rol",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    Nombre = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Descripcion = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Rol", x => x.Id);
                    table.CheckConstraint("CK_Rol_DosRoles", "[Nombre] IN ('administrador','operador')");
                });

            migrationBuilder.CreateTable(
                name: "VersionModelo",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    Tipo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Identificador = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Descripcion = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Estado = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    ActivadaUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_VersionModelo", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "Interseccion",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    CorredorId = table.Column<int>(type: "int", nullable: false),
                    Nombre = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Latitud = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    Longitud = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    EstadoOperativo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Interseccion", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Interseccion_Corredor_CorredorId",
                        column: x => x.CorredorId,
                        principalTable: "Corredor",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Reporte",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    CorredorId = table.Column<int>(type: "int", nullable: false),
                    Tipo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    DesdeUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    HastaUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    GeneradoUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    Modo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Estado = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Reporte", x => x.Id);
                    table.CheckConstraint("CK_Reporte_Periodo", "[HastaUtc] > [DesdeUtc]");
                    table.ForeignKey(
                        name: "FK_Reporte_Corredor_CorredorId",
                        column: x => x.CorredorId,
                        principalTable: "Corredor",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Usuario",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    RolId = table.Column<int>(type: "int", nullable: false),
                    IdentificadorIdp = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Nombre = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Activo = table.Column<bool>(type: "bit", nullable: false),
                    MfaHabilitado = table.Column<bool>(type: "bit", nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Usuario", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Usuario_Rol_RolId",
                        column: x => x.RolId,
                        principalTable: "Rol",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Acceso",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    InterseccionId = table.Column<int>(type: "int", nullable: false),
                    Identificador = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Aproximacion = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    LongitudCrucePeatonalMetros = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Acceso", x => x.Id);
                    table.CheckConstraint("CK_Acceso_LongitudPositiva", "[LongitudCrucePeatonalMetros] > 0");
                    table.ForeignKey(
                        name: "FK_Acceso_Interseccion_InterseccionId",
                        column: x => x.InterseccionId,
                        principalTable: "Interseccion",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Alerta",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    InterseccionId = table.Column<int>(type: "int", nullable: false),
                    Tipo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    FechaUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    Severidad = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Descripcion = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Estado = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Alerta", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Alerta_Interseccion_InterseccionId",
                        column: x => x.InterseccionId,
                        principalTable: "Interseccion",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "ConfigTecnica",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    InterseccionId = table.Column<int>(type: "int", nullable: false),
                    Version = table.Column<int>(type: "int", nullable: false),
                    VerdeMinSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    VerdeMaxSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    AmbarSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    TodoRojoSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    ExtensionPrioridadSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    ResponsableTecnico = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    AprobadaUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    Estado = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ConfigTecnica", x => x.Id);
                    table.CheckConstraint("CK_ConfigTecnica_Limites", "[VerdeMinSegundos] > 0 AND [VerdeMaxSegundos] >= [VerdeMinSegundos] AND [ExtensionPrioridadSegundos] BETWEEN 0 AND 10");
                    table.ForeignKey(
                        name: "FK_ConfigTecnica_Interseccion_InterseccionId",
                        column: x => x.InterseccionId,
                        principalTable: "Interseccion",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "ControladorLocal",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    InterseccionId = table.Column<int>(type: "int", nullable: false),
                    Tipo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Protocolo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Ubicacion = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Emulado = table.Column<bool>(type: "bit", nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ControladorLocal", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ControladorLocal_Interseccion_InterseccionId",
                        column: x => x.InterseccionId,
                        principalTable: "Interseccion",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Bitacora",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    UsuarioId = table.Column<int>(type: "int", nullable: false),
                    Operacion = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    FechaUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    Motivo = table.Column<string>(type: "nvarchar(1000)", maxLength: 1000, nullable: false),
                    ObjetoTipo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    ObjetoId = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    ValorAnterior = table.Column<string>(type: "nvarchar(max)", maxLength: 16000, nullable: false),
                    ValorPosterior = table.Column<string>(type: "nvarchar(max)", maxLength: 16000, nullable: false),
                    MfaVerificado = table.Column<bool>(type: "bit", nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Bitacora", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Bitacora_Usuario_UsuarioId",
                        column: x => x.UsuarioId,
                        principalTable: "Usuario",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Carril",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    AccesoId = table.Column<int>(type: "int", nullable: false),
                    Numero = table.Column<int>(type: "int", nullable: false),
                    Sentido = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Carril", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Carril_Acceso_AccesoId",
                        column: x => x.AccesoId,
                        principalTable: "Acceso",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "FuenteDeteccion",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    AccesoId = table.Column<int>(type: "int", nullable: false),
                    TipoCamara = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Ubicacion = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Protocolo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Activa = table.Column<bool>(type: "bit", nullable: false),
                    ModeloIa = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    UmbralConfianza = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_FuenteDeteccion", x => x.Id);
                    table.ForeignKey(
                        name: "FK_FuenteDeteccion_Acceso_AccesoId",
                        column: x => x.AccesoId,
                        principalTable: "Acceso",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Plan",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    InterseccionId = table.Column<int>(type: "int", nullable: false),
                    ConfigTecnicaId = table.Column<int>(type: "int", nullable: false),
                    Version = table.Column<int>(type: "int", nullable: false),
                    Tipo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    MetodoCalculo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    CicloSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    CalculadoUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    Estado = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Plan", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Plan_ConfigTecnica_ConfigTecnicaId",
                        column: x => x.ConfigTecnicaId,
                        principalTable: "ConfigTecnica",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_Plan_Interseccion_InterseccionId",
                        column: x => x.InterseccionId,
                        principalTable: "Interseccion",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Medicion",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    CarrilId = table.Column<int>(type: "int", nullable: false),
                    FuenteDeteccionId = table.Column<int>(type: "int", nullable: false),
                    MensajeId = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    InicioUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    FinUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    ClaseVehiculo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Cantidad = table.Column<int>(type: "int", nullable: false),
                    ColaEstimadaMetros = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Medicion", x => x.Id);
                    table.CheckConstraint("CK_Medicion_Intervalo", "[FinUtc] > [InicioUtc] AND [Cantidad] >= 0");
                    table.ForeignKey(
                        name: "FK_Medicion_Carril_CarrilId",
                        column: x => x.CarrilId,
                        principalTable: "Carril",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_Medicion_FuenteDeteccion_FuenteDeteccionId",
                        column: x => x.FuenteDeteccionId,
                        principalTable: "FuenteDeteccion",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "EventoPrioridad",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    InterseccionId = table.Column<int>(type: "int", nullable: false),
                    PlanId = table.Column<int>(type: "int", nullable: false),
                    Tipo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Origen = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    DetectadoUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    AtendidoUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    Resultado = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Accion = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    ExtensionSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    Ciclo = table.Column<int>(type: "int", nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_EventoPrioridad", x => x.Id);
                    table.CheckConstraint("CK_EventoPrioridad_Tiempo", "[AtendidoUtc] >= [DetectadoUtc] AND [ExtensionSegundos] BETWEEN 0 AND 10");
                    table.ForeignKey(
                        name: "FK_EventoPrioridad_Interseccion_InterseccionId",
                        column: x => x.InterseccionId,
                        principalTable: "Interseccion",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_EventoPrioridad_Plan_PlanId",
                        column: x => x.PlanId,
                        principalTable: "Plan",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Fase",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    PlanId = table.Column<int>(type: "int", nullable: false),
                    AccesoId = table.Column<int>(type: "int", nullable: false),
                    Orden = table.Column<int>(type: "int", nullable: false),
                    Tipo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    VerdeSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    AmbarSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    TodoRojoSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    TiempoPeatonalSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Fase", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Fase_Acceso_AccesoId",
                        column: x => x.AccesoId,
                        principalTable: "Acceso",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_Fase_Plan_PlanId",
                        column: x => x.PlanId,
                        principalTable: "Plan",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "ValidacionSumo",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    PlanId = table.Column<int>(type: "int", nullable: false),
                    Escenario = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Semilla = table.Column<int>(type: "int", nullable: false),
                    EjecutadaUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    Resultado = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Motivo = table.Column<string>(type: "nvarchar(1000)", maxLength: 1000, nullable: false),
                    DemoraGlobalBaseSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    DemoraGlobalCandidataSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    CumpleMinimoPeatonal = table.Column<bool>(type: "bit", nullable: false),
                    CumpleDespejePeatonal = table.Column<bool>(type: "bit", nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ValidacionSumo", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ValidacionSumo_Plan_PlanId",
                        column: x => x.PlanId,
                        principalTable: "Plan",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "EstadoControl",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    ControladorLocalId = table.Column<int>(type: "int", nullable: false),
                    PlanId = table.Column<int>(type: "int", nullable: false),
                    FaseId = table.Column<int>(type: "int", nullable: false),
                    FechaUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    ComunicacionDisponible = table.Column<bool>(type: "bit", nullable: false),
                    Modo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_EstadoControl", x => x.Id);
                    table.ForeignKey(
                        name: "FK_EstadoControl_ControladorLocal_ControladorLocalId",
                        column: x => x.ControladorLocalId,
                        principalTable: "ControladorLocal",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_EstadoControl_Fase_FaseId",
                        column: x => x.FaseId,
                        principalTable: "Fase",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_EstadoControl_Plan_PlanId",
                        column: x => x.PlanId,
                        principalTable: "Plan",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "MetricaPorAcceso",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    ValidacionSumoId = table.Column<int>(type: "int", nullable: false),
                    AccesoId = table.Column<int>(type: "int", nullable: false),
                    Grupo = table.Column<string>(type: "nvarchar(500)", maxLength: 500, nullable: false),
                    VehiculosBase = table.Column<int>(type: "int", nullable: false),
                    VehiculosCandidatos = table.Column<int>(type: "int", nullable: false),
                    DemoraBaseSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    DemoraCandidataSegundos = table.Column<decimal>(type: "decimal(18,6)", precision: 18, scale: 6, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_MetricaPorAcceso", x => x.Id);
                    table.ForeignKey(
                        name: "FK_MetricaPorAcceso_Acceso_AccesoId",
                        column: x => x.AccesoId,
                        principalTable: "Acceso",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_MetricaPorAcceso_ValidacionSumo_ValidacionSumoId",
                        column: x => x.ValidacionSumoId,
                        principalTable: "ValidacionSumo",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Recomendacion",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    ValidacionSumoId = table.Column<int>(type: "int", nullable: false),
                    EmitidaUtc = table.Column<DateTimeOffset>(type: "datetimeoffset", nullable: false),
                    JustificacionTecnica = table.Column<string>(type: "nvarchar(1000)", maxLength: 1000, nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Recomendacion", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Recomendacion_ValidacionSumo_ValidacionSumoId",
                        column: x => x.ValidacionSumoId,
                        principalTable: "ValidacionSumo",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "IX_Acceso_InterseccionId_Identificador",
                table: "Acceso",
                columns: new[] { "InterseccionId", "Identificador" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Alerta_InterseccionId",
                table: "Alerta",
                column: "InterseccionId");

            migrationBuilder.CreateIndex(
                name: "IX_Bitacora_UsuarioId",
                table: "Bitacora",
                column: "UsuarioId");

            migrationBuilder.CreateIndex(
                name: "IX_Carril_AccesoId_Numero",
                table: "Carril",
                columns: new[] { "AccesoId", "Numero" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_ConfigTecnica_InterseccionId_Version",
                table: "ConfigTecnica",
                columns: new[] { "InterseccionId", "Version" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_ControladorLocal_InterseccionId",
                table: "ControladorLocal",
                column: "InterseccionId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Corredor_Nombre",
                table: "Corredor",
                column: "Nombre",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Decisiones_PlanId_Version",
                table: "Decisiones",
                columns: new[] { "PlanId", "Version" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Decisiones_SolicitudId",
                table: "Decisiones",
                column: "SolicitudId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_EstadoControl_ControladorLocalId_Prueba_FechaUtc",
                table: "EstadoControl",
                columns: new[] { "ControladorLocalId", "Prueba", "FechaUtc" });

            migrationBuilder.CreateIndex(
                name: "IX_EstadoControl_FaseId",
                table: "EstadoControl",
                column: "FaseId");

            migrationBuilder.CreateIndex(
                name: "IX_EstadoControl_PlanId",
                table: "EstadoControl",
                column: "PlanId");

            migrationBuilder.CreateIndex(
                name: "IX_Evaluaciones_PlanId_Version",
                table: "Evaluaciones",
                columns: new[] { "PlanId", "Version" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_EventoPrioridad_InterseccionId",
                table: "EventoPrioridad",
                column: "InterseccionId");

            migrationBuilder.CreateIndex(
                name: "IX_EventoPrioridad_PlanId",
                table: "EventoPrioridad",
                column: "PlanId");

            migrationBuilder.CreateIndex(
                name: "IX_Fase_AccesoId",
                table: "Fase",
                column: "AccesoId");

            migrationBuilder.CreateIndex(
                name: "IX_Fase_PlanId_Orden",
                table: "Fase",
                columns: new[] { "PlanId", "Orden" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_FuenteDeteccion_AccesoId",
                table: "FuenteDeteccion",
                column: "AccesoId");

            migrationBuilder.CreateIndex(
                name: "IX_Interseccion_CorredorId_Nombre",
                table: "Interseccion",
                columns: new[] { "CorredorId", "Nombre" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Medicion_CarrilId",
                table: "Medicion",
                column: "CarrilId");

            migrationBuilder.CreateIndex(
                name: "IX_Medicion_FuenteDeteccionId",
                table: "Medicion",
                column: "FuenteDeteccionId");

            migrationBuilder.CreateIndex(
                name: "IX_Medicion_MensajeId",
                table: "Medicion",
                column: "MensajeId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_MetricaPorAcceso_AccesoId",
                table: "MetricaPorAcceso",
                column: "AccesoId");

            migrationBuilder.CreateIndex(
                name: "IX_MetricaPorAcceso_ValidacionSumoId_AccesoId_Grupo",
                table: "MetricaPorAcceso",
                columns: new[] { "ValidacionSumoId", "AccesoId", "Grupo" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Plan_ConfigTecnicaId",
                table: "Plan",
                column: "ConfigTecnicaId");

            migrationBuilder.CreateIndex(
                name: "IX_Plan_InterseccionId_Version_Tipo",
                table: "Plan",
                columns: new[] { "InterseccionId", "Version", "Tipo" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Recomendacion_ValidacionSumoId",
                table: "Recomendacion",
                column: "ValidacionSumoId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Reporte_CorredorId",
                table: "Reporte",
                column: "CorredorId");

            migrationBuilder.CreateIndex(
                name: "IX_Rol_Nombre",
                table: "Rol",
                column: "Nombre",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Usuario_IdentificadorIdp",
                table: "Usuario",
                column: "IdentificadorIdp",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_Usuario_RolId",
                table: "Usuario",
                column: "RolId");

            migrationBuilder.CreateIndex(
                name: "IX_ValidacionSumo_PlanId",
                table: "ValidacionSumo",
                column: "PlanId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_VersionModelo_Identificador",
                table: "VersionModelo",
                column: "Identificador",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "Alerta");

            migrationBuilder.DropTable(
                name: "Bitacora");

            migrationBuilder.DropTable(
                name: "Decisiones");

            migrationBuilder.DropTable(
                name: "EstadoControl");

            migrationBuilder.DropTable(
                name: "Evaluaciones");

            migrationBuilder.DropTable(
                name: "EventoPrioridad");

            migrationBuilder.DropTable(
                name: "Medicion");

            migrationBuilder.DropTable(
                name: "MetricaPorAcceso");

            migrationBuilder.DropTable(
                name: "Recomendacion");

            migrationBuilder.DropTable(
                name: "Reporte");

            migrationBuilder.DropTable(
                name: "VersionModelo");

            migrationBuilder.DropTable(
                name: "Usuario");

            migrationBuilder.DropTable(
                name: "ControladorLocal");

            migrationBuilder.DropTable(
                name: "Fase");

            migrationBuilder.DropTable(
                name: "Carril");

            migrationBuilder.DropTable(
                name: "FuenteDeteccion");

            migrationBuilder.DropTable(
                name: "ValidacionSumo");

            migrationBuilder.DropTable(
                name: "Rol");

            migrationBuilder.DropTable(
                name: "Acceso");

            migrationBuilder.DropTable(
                name: "Plan");

            migrationBuilder.DropTable(
                name: "ConfigTecnica");

            migrationBuilder.DropTable(
                name: "Interseccion");

            migrationBuilder.DropTable(
                name: "Corredor");
        }
    }
}
