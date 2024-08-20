package net.jsussman.ioedict;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

public class App {
  public static void main(String[] args) {
    System.out.println("Starting application!");

    Path source = Paths.get("input.txt");
    Path destination = Paths.get("output.txt");
    try {
      Files.copy(source, destination);
    } catch (IOException e) {
      e.printStackTrace();
    }
  }
}
