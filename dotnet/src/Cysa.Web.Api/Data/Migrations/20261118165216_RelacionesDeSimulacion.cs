using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Cysa.Web.Api.Data.Migrations
{
    /// <inheritdoc />
    public partial class RelacionesDeSimulacion : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "FaseAcceso",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    FaseId = table.Column<int>(type: "int", nullable: false),
                    AccesoId = table.Column<int>(type: "int", nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_FaseAcceso", x => x.Id);
                    table.ForeignKey(
                        name: "FK_FaseAcceso_Acceso_AccesoId",
                        column: x => x.AccesoId,
                        principalTable: "Acceso",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_FaseAcceso_Fase_FaseId",
                        column: x => x.FaseId,
                        principalTable: "Fase",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "ValidacionEvento",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    ValidacionSumoId = table.Column<int>(type: "int", nullable: false),
                    EventoPrioridadId = table.Column<int>(type: "int", nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ValidacionEvento", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ValidacionEvento_EventoPrioridad_EventoPrioridadId",
                        column: x => x.EventoPrioridadId,
                        principalTable: "EventoPrioridad",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_ValidacionEvento_ValidacionSumo_ValidacionSumoId",
                        column: x => x.ValidacionSumoId,
                        principalTable: "ValidacionSumo",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "ValidacionMedicion",
                columns: table => new
                {
                    Id = table.Column<int>(type: "int", nullable: false)
                        .Annotation("SqlServer:Identity", "1, 1"),
                    ValidacionSumoId = table.Column<int>(type: "int", nullable: false),
                    MedicionId = table.Column<int>(type: "int", nullable: false),
                    Prueba = table.Column<bool>(type: "bit", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ValidacionMedicion", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ValidacionMedicion_Medicion_MedicionId",
                        column: x => x.MedicionId,
                        principalTable: "Medicion",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_ValidacionMedicion_ValidacionSumo_ValidacionSumoId",
                        column: x => x.ValidacionSumoId,
                        principalTable: "ValidacionSumo",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "IX_FaseAcceso_AccesoId",
                table: "FaseAcceso",
                column: "AccesoId");

            migrationBuilder.CreateIndex(
                name: "IX_FaseAcceso_FaseId_AccesoId",
                table: "FaseAcceso",
                columns: new[] { "FaseId", "AccesoId" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_ValidacionEvento_EventoPrioridadId",
                table: "ValidacionEvento",
                column: "EventoPrioridadId");

            migrationBuilder.CreateIndex(
                name: "IX_ValidacionEvento_ValidacionSumoId_EventoPrioridadId",
                table: "ValidacionEvento",
                columns: new[] { "ValidacionSumoId", "EventoPrioridadId" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_ValidacionMedicion_MedicionId",
                table: "ValidacionMedicion",
                column: "MedicionId");

            migrationBuilder.CreateIndex(
                name: "IX_ValidacionMedicion_ValidacionSumoId_MedicionId",
                table: "ValidacionMedicion",
                columns: new[] { "ValidacionSumoId", "MedicionId" },
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "FaseAcceso");

            migrationBuilder.DropTable(
                name: "ValidacionEvento");

            migrationBuilder.DropTable(
                name: "ValidacionMedicion");
        }
    }
}
