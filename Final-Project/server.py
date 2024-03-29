import http.server
import socketserver
import termcolor
from pathlib import Path
import jinja2 as j
from urllib.parse import parse_qs, urlparse
import http.client
import my_modules
from Seq1 import Seq

HTML_FOLDER = "./html/"
PARAMS = '?content-type=application/json' #if we want to append a parameter -> ej params should be &param1=a -> convert params -> params = "&number=" + str(n_sequence)
genes_dict = {"SRCAP": "ENSG00000080603", "FRAT1": "ENSG00000165879", "ADA": "ENSG00000196839", "FXN": "ENSG00000165060","RNU6_269P":"ENSG00000212379", "MIR633":"ENSG00000207552", "TTTY4C":"ENSG00000228296", "RBMY2YP":"ENSG00000227633", "FGFR3":"ENSG00000068078", "KDR":"ENSG00000128052", "ANK2":"ENSG00000145362"}
genes_names = []
for k, v in genes_dict.items():
    genes_names.append(k)

def read_html_file(filename):
    contents = Path(HTML_FOLDER + filename).read_text()
    contents = j.Template(contents)
    return contents

PORT = 8080
socketserver.TCPServer.allow_reuse_address = True

class TestHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        global length
        termcolor.cprint(self.requestline, 'green')
        url_path = urlparse(self.path)
        path = url_path.path #esto quita las interrogaciones
        arguments = parse_qs(url_path.query)
        print("The new path is:", url_path.path)
        print("my arg", arguments)
        #BASIC LEVEL SERVICES
        if self.path == "/":
            contents = read_html_file('index.html').render(context={"genes": genes_names, "g": genes_names })
        elif path == "/listSpecies":
            try:
                n_species = int(arguments["limit"][0])
                dict_answer = my_modules.requesting("info/species", PARAMS)
                list_species = []
                total_n_species = []
                for d in dict_answer["species"]:
                    total_n_species.append(d["name"])
                if n_species > len(total_n_species) or n_species <= 0:
                    contents = read_html_file("list_of_species.html").render(context={"total_number": len(total_n_species), "my_lim": n_species, "species": ["Error. Can´t provide a list with that number"]})
                else:
                    for i in range(n_species):
                        list_species.append(dict_answer["species"][i]["name"])
                    filename = "list_of_species.html"
                    d = {"total_number": len(total_n_species), "my_lim": n_species,"species": list_species}
                    contents = my_modules.check_json(arguments, filename, d)
            except ValueError:
                contents = read_html_file("error.html").render()
            except KeyError:
                contents = read_html_file("error.html").render()
        elif path == "/karyotype":
            try:
                specie = arguments["specie"][0]
                ens_answer = my_modules.requesting("info/assembly/" + specie, PARAMS)
                filename = "karyotype.html"
                d = {"chromosomes": ens_answer["karyotype"]}
                contents = my_modules.check_json(arguments, filename, d)
                if ens_answer["karyotype"] == []:
                    contents = read_html_file("error.html").render()
            except KeyError:
                contents = read_html_file("error.html").render()
        elif path == "/chromosomeLength":
            try:
                specie = arguments["name"][0]
                chromosome = arguments["number"][0]
                ens_answer = my_modules.requesting("info/assembly/" + specie, PARAMS)
                names_list = []
                for d in ens_answer["top_level_region"]:
                    names_list.append(d["name"])
                for d in ens_answer["top_level_region"]:
                    if d["name"] == chromosome:
                        length = d["length"]
                d = {"length": length}
                if chromosome not in names_list:
                    contents = read_html_file("error.html").render()
                else:
                    contents = my_modules.check_json(arguments, "chromosome_length.html", d)
            except KeyError:
                contents = read_html_file("chromosome_length.html").render(context={"length": my_modules.change_message()})
            except NameError:
                contents = read_html_file("chromosome_length.html").render(context={"length": my_modules.change_message()})
        #MEDIUM LEVEL SERVICES
        elif path == "/geneSeq":
            gene_name = arguments["gene_name"][0]
            seq_id = genes_dict[gene_name]
            ens_answer = my_modules.requesting("sequence/id/" + str(seq_id), PARAMS)
            contents = my_modules.check_json(arguments, "human_gene_seq.html", {"gene": gene_name, "sequence": ens_answer['seq']})
        elif path == "/geneInfo":
            gene_name = arguments["gene_name"][0]
            seq_id = genes_dict[gene_name]
            ens_answer = my_modules.requesting("sequence/id/" + str(seq_id), PARAMS)
            info_list = ens_answer["desc"].split(":")
            contents = my_modules.check_json(arguments, "info_gene.html", {"gene": gene_name, "start": info_list[3], "end": info_list[4], "length": len(ens_answer["seq"]), "name": info_list[1]})
        elif path == "/geneCalc":
            gene_name = arguments["g_name"][0]
            seq_id = genes_dict[gene_name]
            ens_answer = my_modules.requesting("sequence/id/" + str(seq_id), PARAMS)
            s = Seq(ens_answer['seq'])
            bases_dict = s.count()
            contents = my_modules.check_json(arguments, "gene_calc.html",{"gene": gene_name, "sequence": ens_answer['seq'], "length": s.len(), "percentages": my_modules.convert_message(bases_dict, s.len())})
        elif path == "/geneList":
            try:
                chromosome = arguments["chromo"][0]
                start = str(arguments["start"][0])
                end = str(arguments["end"][0])
                request = chromosome + ":" + start + "-" + end
                ens_answer = my_modules.requesting("/phenotype/region/homo_sapiens/" + request, PARAMS)
                names_list = []
                for d in ens_answer:
                    for l in d["phenotype_associations"]:
                        try:
                            names_list.append(l["attributes"]["associated_gene"])
                        except KeyError:
                            pass
                if not names_list:
                    contents = read_html_file("gene_list.html").render(context={"chromo": chromosome, "names": ["ERROR. The start and end positions may be wrong"]})
                else:
                    contents = my_modules.check_json(arguments, "gene_list.html", {"chromo": chromosome, "names": names_list})
            except KeyError:
                contents = read_html_file("error.html").render()
            except TypeError:
                contents = read_html_file("error.html").render()
        else:
            contents = "I am the happy server :)"
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(str.encode(contents)))
        self.end_headers()
        self.wfile.write(str.encode(contents))
        return

Handler = TestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:

    print("Serving at PORT", PORT)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("")
        print("Stopped by the user")
        httpd.server_close()